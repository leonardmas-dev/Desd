"""Use Case 1 job workers and external-producer message commands (Python stdlib)."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date
import json
import logging
import math
import os
from pathlib import Path
import sqlite3
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import uuid

LOG = logging.getLogger(__name__)
JOB_TYPES = (
    "validate-product-details", "verify-organic-cert", "publish-product",
    "request-product-correction", "notify-product-published",
)
PRODUCT_FIELDS = (
    "productId", "productName", "description", "productCategory", "productPrice",
    "stockQuantity", "availableStart", "availableEnd", "productOrigin",
    "productAllergen", "organicClaimed", "organicCertNum", "harvestDate", "bestBeforeDate",
)
TEST_FIELDS = ("simulatedCertification", "certificationTimeout", "certificationRetrySeconds")


class ApiError(Exception):
    def __init__(self, status, path):
        self.status = status
        super().__init__(f"HTTP {status} at {path}")


class BusinessError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def post_json(url, payload, headers=None, timeout=40):
    request = Request(url, data=json.dumps(payload).encode(), method="POST",
                      headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            return json.loads(body) if body else {}
    except HTTPError as error:
        error.close()
        raise ApiError(error.code, urlparse(url).path) from error


class TokenProvider:
    """Use an existing bearer token, or refresh existing OAuth client credentials."""

    def __init__(self):
        self.token = os.environ.get("CAMUNDA_BEARER_TOKEN", "")
        self.expires = float("inf") if self.token else 0
        self.lock = threading.Lock()

    def get(self):
        with self.lock:
            if self.token and self.expires > time.time() + 30:
                return self.token
            names = ("CAMUNDA_TOKEN_URL", "CAMUNDA_CLIENT_ID", "CAMUNDA_CLIENT_SECRET")
            if not all(os.environ.get(name) for name in names):
                return ""
            token_url = os.environ["CAMUNDA_TOKEN_URL"]
            if urlparse(token_url).scheme != "https":
                raise ValueError("CAMUNDA_TOKEN_URL must use HTTPS")
            data = post_json(token_url, {
                "grant_type": "client_credentials",
                "client_id": os.environ["CAMUNDA_CLIENT_ID"],
                "client_secret": os.environ["CAMUNDA_CLIENT_SECRET"],
                "audience": os.environ.get("CAMUNDA_TOKEN_AUDIENCE", "zeebe.camunda.io"),
            })
            self.token = data["access_token"]
            self.expires = time.time() + data.get("expires_in", 300)
            return self.token


class CamundaClient:
    def __init__(self, base_url, token_provider=None):
        self.base = base_url.rstrip("/")
        if not self.base.endswith("/v2"):
            self.base += "/v2"
        parsed = urlparse(self.base)
        self.local = parsed.hostname in ("localhost", "127.0.0.1", "::1")
        if parsed.scheme != "https" and not self.local:
            raise ValueError("The cluster API must use HTTPS")
        self.tokens = token_provider or TokenProvider()
        self.tenant = os.environ.get("CAMUNDA_TENANT_ID", "")

    def post(self, path, payload):
        token = self.tokens.get()
        if not token and not self.local:
            raise ValueError("Configure an existing Camunda bearer token or OAuth client")
        headers = {"Authorization": "Bearer " + token} if token else {}
        return post_json(self.base + path, payload, headers)

    def activate(self, job_type, maximum):
        payload = {"type": job_type, "worker": "brfn-validation", "timeout": 60000,
                   "maxJobsToActivate": maximum, "requestTimeout": -1}
        if self.tenant:
            payload["tenantIds"] = [self.tenant]
        return self.post("/jobs/activation", payload).get("jobs", [])

    def complete(self, job, variables):
        return self.post(f"/jobs/{job['jobKey']}/completion", {"variables": variables})

    def throw(self, job, error):
        return self.post(f"/jobs/{job['jobKey']}/error", {
            "errorCode": error.code, "errorMessage": str(error)})

    def fail(self, job, error):
        return self.post(f"/jobs/{job['jobKey']}/failure", {
            "retries": max(0, job.get("retries", 1) - 1),
            "errorMessage": str(error), "retryBackOff": 1000})

    def publish(self, name, correlation, variables, message_id):
        payload = {"name": name, "correlationKey": correlation, "variables": variables,
                   "messageId": message_id, "timeToLive": 300000}
        if self.tenant:
            payload["tenantId"] = self.tenant
        return self.post("/messages/publication", payload)


def validate_product(values):
    """Use the shared form keys; keep policy independent of UI field validation."""
    errors = []
    for key, label in (
        ("productId", "Product ID"), ("productName", "Product name"),
        ("description", "Description"), ("productCategory", "Category"),
        ("productOrigin", "Farm origin"),
    ):
        if not isinstance(values.get(key), str) or not values[key].strip():
            errors.append(f"{label} is required.")
    price = values.get("productPrice")
    if type(price) not in (int, float) or not math.isfinite(price) or price < 0:
        errors.append("Price must be a non-negative number.")
    quantity = values.get("stockQuantity")
    if (type(quantity) not in (int, float) or not math.isfinite(quantity)
            or quantity <= 0 or quantity != int(quantity)):
        errors.append("Initial quantity must be a positive whole number.")
    dates = {}
    for key, required in (("availableStart", True), ("availableEnd", True),
                          ("harvestDate", False), ("bestBeforeDate", False)):
        value = values.get(key)
        if value in (None, "") and not required:
            continue
        try:
            if not isinstance(value, str):
                raise ValueError
            dates[key] = date.fromisoformat(value)
            if dates[key].isoformat() != value:
                raise ValueError
        except ValueError:
            errors.append(f"{key} must be a date in YYYY-MM-DD format.")
    if ("availableStart" in dates and "availableEnd" in dates
            and dates["availableStart"] > dates["availableEnd"]):
        errors.append("Availability end must not precede its start.")
    if ("harvestDate" in dates and "bestBeforeDate" in dates
            and dates["harvestDate"] > dates["bestBeforeDate"]):
        errors.append("Best-before date must not precede harvest date.")
    organic = values.get("organicClaimed")
    if type(organic) is not bool:
        errors.append("Organic claimed must be a Boolean.")
    if organic is True and (not isinstance(values.get("organicCertNum"), str)
                            or not values["organicCertNum"].strip()):
        errors.append("An organic certification number is required for an organic claim.")
    return {"validationPassed": not errors, "validationErrors": errors,
            "validationMessage": "\n".join(errors), "organicClaimed": organic is True}


class Catalogue:
    """Persistent demonstration catalogue, separate from a production marketplace."""
    def __init__(self, filename):
        self.filename = str(filename)
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.filename)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS products "
                       "(product_id TEXT PRIMARY KEY, submission_id TEXT, payload TEXT NOT NULL)")

    def publish(self, values, today=None):
        checked = validate_product(values)
        if values.get("validationPassed") is not True or not checked["validationPassed"]:
            raise BusinessError("VALIDATION_REQUIRED", "Publication requires validated product data")
        if values["organicClaimed"] and values.get("certificationResult") != "valid":
            raise BusinessError("CERTIFICATION_REQUIRED", "The organic claim has not been verified")
        today = today or date.today()
        available = (date.fromisoformat(values["availableStart"]) <= today
                     <= date.fromisoformat(values["availableEnd"]))
        product = {key: values.get(key) for key in PRODUCT_FIELDS}
        product.update(published=True, available=available,
                       organicBadge=values["organicClaimed"],
                       catalogueStatus="ACTIVE" if available else "UNAVAILABLE_OFF_SEASON")
        with closing(sqlite3.connect(self.filename)) as db, db:
            db.execute("INSERT INTO products VALUES (?, ?, ?) ON CONFLICT(product_id) DO UPDATE SET "
                       "submission_id=excluded.submission_id, payload=excluded.payload",
                       (values["productId"], values["submissionId"], json.dumps(product)))
        return {key: product[key] for key in ("published", "available", "organicBadge", "catalogueStatus")}


class ValidationWorker:
    def __init__(self, client, verifier_url, catalogue, verifier_timeout=35):
        self.client = client
        self.verifier_url = verifier_url
        self.catalogue = catalogue
        self.verifier_timeout = verifier_timeout

    def verify(self, values):
        certificate = values.get("organicCertNum")
        if not isinstance(certificate, str) or not certificate.strip():
            return {"certificationResult": "invalid"}
        payload = {"certificateNumber": certificate, "farmOrigin": values.get("productOrigin")}
        # Scenario overrides are honoured only when the local mock is explicitly
        # started with --allow-scenarios. Absence never implies success.
        if values.get("simulatedCertification") is not None:
            payload["scenario"] = values["simulatedCertification"]
        try:
            response = post_json(self.verifier_url, payload, timeout=self.verifier_timeout)
        except ApiError as error:
            if error.status == 503:
                return {"certificationResult": "unavailable"}
            raise
        except (URLError, TimeoutError, ConnectionError):
            return {"certificationResult": "unavailable"}
        if response.get("errorCode") == "SERVICE_UNAVAILABLE":
            raise BusinessError("SERVICE_UNAVAILABLE", "Verification service unavailable")
        result = response.get("result")
        if result not in ("valid", "invalid", "unavailable"):
            # The parent default route requires review for an unrecognised result.
            result = "unexpected"
        return {"certificationResult": result}

    def handle(self, job):
        values = job["variables"]
        job_type = job["type"]
        if job_type == "validate-product-details":
            return validate_product(values)
        if job_type == "verify-organic-cert":
            return self.verify(values)
        if job_type == "publish-product":
            return self.catalogue.publish(values)
        if job_type == "request-product-correction":
            errors = values.get("validationErrors") or []
            if not errors and values.get("certificationResult") == "invalid":
                errors = ["Organic certification is invalid. Correct the certificate or explicitly "
                          "change the claim, then resubmit for validation."]
            if not errors:
                errors = ["Verification was unresolved or a retry was not approved. Review and correct the submission."]
            feedback = {"validationErrors": errors, "validationMessage": "\n".join(errors)}
            self.client.publish("brfn.product.correction-requested", values["submissionId"],
                                feedback, "correction-" + str(job["jobKey"]))
            return feedback
        if job_type == "notify-product-published":
            self.client.publish("brfn.product.published", values["submissionId"],
                                {"productId": values["productId"], "published": True},
                                "published-" + str(job["jobKey"]))
            return {"publicationConfirmed": True}
        raise ValueError("Unsupported job type: " + job_type)

    def process(self, job):
        try:
            self.client.complete(job, self.handle(job))
        except BusinessError as error:
            self._finish(self.client.throw, job, error)
        except ApiError as error:
            if error.status in (404, 409):
                LOG.info("Job %s no longer active; parent may have cancelled it", job["jobKey"])
            else:
                self._finish(self.client.fail, job, error)
        except Exception as error:
            self._finish(self.client.fail, job, error)

    @staticmethod
    def _finish(command, job, error):
        try:
            command(job, error)
        except ApiError as finish_error:
            if finish_error.status not in (404, 409):
                LOG.error("Could not report job %s: %s", job["jobKey"], finish_error)
        except (URLError, TimeoutError, ConnectionError) as finish_error:
            LOG.warning("Could not report job %s; its activation lease will expire: %s",
                        job["jobKey"], finish_error)

    def run(self, concurrency=8):
        # A slow verification request must not prevent other retries/jobs from running.
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            pending = set()
            while True:
                pending = {future for future in pending if not future.done()}
                for job_type in JOB_TYPES:
                    free = concurrency - len(pending)
                    if free <= 0:
                        break
                    try:
                        jobs = self.client.activate(job_type, free)
                    except ApiError as error:
                        if error.status in (401, 403):
                            raise
                        LOG.warning("Activation failed: %s", error)
                        jobs = []
                    except (URLError, TimeoutError, ConnectionError) as error:
                        LOG.warning("Cluster temporarily unreachable: %s", error)
                        jobs = []
                    for job in jobs:
                        pending.add(pool.submit(self.process, job))
                time.sleep(0.25)


def producer_message(client, filename, correlation=None):
    """Publish whitelisted form fields; never overwrite Marketplace control state."""
    supplied = json.loads(Path(filename).read_text())
    correlation = correlation or str(uuid.uuid4())
    values = {key: supplied[key] for key in PRODUCT_FIELDS + TEST_FIELDS if key in supplied}
    values["submissionId"] = correlation
    name = "brfn.product.corrected" if supplied.get("submissionId") else "brfn.product.submitted"
    if supplied.get("submissionId") and supplied["submissionId"] != correlation:
        raise ValueError("Correction submissionId must match the supplied correlation key")
    # Identical corrections may be intentional new submissions. Give each CLI
    # submission its own event ID rather than deduplicating by product contents.
    client.publish(name, correlation, values, name + "-" + str(uuid.uuid4()))
    return correlation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("worker", "submit", "correct"))
    parser.add_argument("--file")
    parser.add_argument("--submission-id")
    args = parser.parse_args()
    client = CamundaClient(os.environ["CAMUNDA_REST_URL"])
    if args.command == "worker":
        worker = ValidationWorker(client, os.environ.get("CERTIFICATION_URL", "http://127.0.0.1:8090/verify"),
                                  Catalogue(os.environ.get("CATALOGUE_DB", "camunda/runtime/catalogue.sqlite3")))
        worker.run()
    else:
        if not args.file:
            parser.error("--file is required")
        data = json.loads(Path(args.file).read_text())
        if args.command == "correct":
            if not args.submission_id or data.get("submissionId") != args.submission_id:
                parser.error("A correction needs --submission-id and the same submissionId in the JSON")
        elif data.get("submissionId"):
            parser.error("Initial submission JSON must not contain submissionId")
        print(producer_message(client, args.file, args.submission_id))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
