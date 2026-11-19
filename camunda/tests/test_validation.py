import copy
from contextlib import closing
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "camunda/service-workers"))
from mock_certification import make_handler
from validation_worker import (
    ApiError, BusinessError, CamundaClient, Catalogue, ValidationWorker,
    producer_message, validate_product,
)


def sample():
    return json.loads((ROOT / "camunda/examples/submission.json").read_text())


class RecordingClient:
    def __init__(self):
        self.events = []
        self.cancelled = False

    def publish(self, *args):
        self.events.append(("message", *args))

    def complete(self, job, values):
        if self.cancelled:
            raise ApiError(404, "/jobs/test/completion")
        self.events.append(("complete", values))

    def throw(self, job, error):
        self.events.append(("error", error.code))

    def fail(self, job, error):
        self.events.append(("failure", str(error)))


class WorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(True, 0.08))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/verify"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.catalogue = Catalogue(Path(self.tmp.name) / "catalogue.sqlite3")
        self.client = RecordingClient()
        self.worker = ValidationWorker(self.client, self.url, self.catalogue, 0.03)
        self.values = sample()
        self.values["submissionId"] = "test-submission-001"

    def job(self, kind, values=None):
        return {"type": kind, "jobKey": "123", "retries": 3,
                "variables": values if values is not None else self.values}

    def test_actual_form_payload_passes(self):
        checked = validate_product(self.values)
        self.assertTrue(checked["validationPassed"], checked)
        self.assertEqual(checked["validationErrors"], [])
        self.assertEqual(checked["validationMessage"], "")

    def seasonal_values(self):
        values = copy.deepcopy(self.values)
        values["seasonalStartDate"] = values.pop("availableStart")
        values["seasonalEndDate"] = values.pop("availableEnd")
        return values

    def test_new_team_seasonal_date_names_are_accepted(self):
        self.assertTrue(validate_product(self.seasonal_values())["validationPassed"])

    def test_conflicting_date_contracts_request_correction(self):
        checked = validate_product({**self.values, "seasonalStartDate": "2026-02-01"})
        self.assertFalse(checked["validationPassed"])
        self.assertIn("must describe the same date", checked["validationMessage"])

    def test_new_form_date_names_do_not_bypass_required_description(self):
        values = self.seasonal_values()
        values.pop("description")
        checked = validate_product(values)
        self.assertFalse(checked["validationPassed"])
        self.assertIn("Description is required", checked["validationMessage"])

    def test_required_fields_report_specific_feedback(self):
        for key in ("productId", "productName", "description", "productCategory", "productOrigin"):
            with self.subTest(key=key):
                values = {k: v for k, v in self.values.items() if k != key}
                checked = validate_product(values)
                self.assertFalse(checked["validationPassed"])
                self.assertTrue(checked["validationMessage"])

    def test_wrong_or_missing_claim_never_becomes_valid_nonorganic(self):
        for claim in (None, "true", "false", 0, 1):
            with self.subTest(claim=claim):
                values = {**self.values, "organicClaimed": claim}
                self.assertFalse(validate_product(values)["validationPassed"])

    def test_zero_fractional_negative_or_boolean_initial_quantity_rejected(self):
        for quantity in (0, -1, 1.5, True, "10"):
            with self.subTest(quantity=quantity):
                self.assertFalse(validate_product({**self.values, "stockQuantity": quantity})["validationPassed"])

    def test_invalid_price_rejected(self):
        for price in (-1, "2", True, float("inf"), float("nan")):
            with self.subTest(price=price):
                self.assertFalse(validate_product({**self.values, "productPrice": price})["validationPassed"])

    def test_reversed_or_malformed_dates_rejected(self):
        for changes in ({"availableEnd": "2025-12-01"}, {"availableStart": "2026-13-99"},
                        {"availableStart": "20260101"}, {"bestBeforeDate": "2026-01-01"}):
            with self.subTest(changes=changes):
                self.assertFalse(validate_product({**self.values, **changes})["validationPassed"])

    def test_relevant_dates_are_optional_but_validated_if_supplied(self):
        values = {k: v for k, v in self.values.items() if k not in ("harvestDate", "bestBeforeDate")}
        self.assertTrue(validate_product(values)["validationPassed"])
        self.assertFalse(validate_product({**values, "harvestDate": "bad date"})["validationPassed"])

    def test_organic_claim_requires_certificate_number(self):
        for value in (None, "", "  ", 123):
            with self.subTest(value=value):
                self.assertFalse(validate_product({**self.values, "organicCertNum": value})["validationPassed"])

    def test_registry_lookup_validates_explicit_fixture(self):
        self.assertEqual(self.worker.verify(self.values), {"certificationResult": "valid"})

    def test_unknown_certificate_without_simulation_does_not_default_valid(self):
        self.assertEqual(self.worker.verify({**self.values, "organicCertNum": "UNKNOWN"}),
                         {"certificationResult": "invalid"})

    def test_missing_certificate_does_not_default_valid(self):
        self.assertEqual(self.worker.verify({**self.values, "organicCertNum": ""}),
                         {"certificationResult": "invalid"})

    def test_http_unavailability_returns_only_result_not_failure_count(self):
        result = self.worker.verify({**self.values, "simulatedCertification": "unavailable"})
        self.assertEqual(result, {"certificationResult": "unavailable"})

    def test_explicit_mock_error_throws_matching_bpmn_error(self):
        values = {**self.values, "simulatedCertification": "error"}
        self.worker.process(self.job("verify-organic-cert", values))
        self.assertEqual(self.client.events, [("error", "SERVICE_UNAVAILABLE")])

    def test_slow_http_request_times_out_without_reporting_valid(self):
        result = self.worker.verify({**self.values, "simulatedCertification": "timeout"})
        self.assertEqual(result, {"certificationResult": "unavailable"})

    def test_cancelled_child_job_does_not_create_another_completion_or_failure(self):
        self.client.cancelled = True
        self.worker.process(self.job("verify-organic-cert"))
        self.assertEqual(self.client.events, [])

    def test_unknown_verifier_response_goes_to_parent_default_review(self):
        with patch("validation_worker.post_json", return_value={"result": "other"}):
            self.assertEqual(self.worker.verify(self.values), {"certificationResult": "unexpected"})

    def test_publication_requires_successful_validation(self):
        with self.assertRaises(BusinessError):
            self.catalogue.publish(self.values)

    def test_publication_revalidates_data_even_when_passed_flag_is_spoofed(self):
        values = {**self.values, "description": "", "validationPassed": True, "certificationResult": "valid"}
        with self.assertRaises(BusinessError):
            self.catalogue.publish(values)

    def test_unverified_organic_claim_cannot_be_published(self):
        for result in (None, "invalid", "unavailable", "unexpected"):
            with self.subTest(result=result), self.assertRaises(BusinessError):
                self.catalogue.publish({**self.values, "validationPassed": True, "certificationResult": result})

    def test_valid_publication_is_persistent_and_idempotent(self):
        values = {**self.values, "validationPassed": True, "certificationResult": "valid"}
        for _ in range(2):
            result = self.catalogue.publish(values, today=date(2026, 11, 19))
            self.assertEqual(result, {"published": True, "available": True,
                                      "organicBadge": True, "catalogueStatus": "ACTIVE"})
        with closing(sqlite3.connect(self.catalogue.filename)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM products").fetchone()[0], 1)

    def test_nonorganic_publication_needs_no_certificate(self):
        values = {**self.values, "validationPassed": True, "organicClaimed": False}
        self.assertFalse(self.catalogue.publish(values, date(2026, 11, 19))["organicBadge"])

    def test_seasonal_date_payload_publishes_with_both_date_contracts_preserved(self):
        values = {**self.seasonal_values(), "validationPassed": True, "certificationResult": "valid"}
        self.assertTrue(self.catalogue.publish(values, date(2026, 11, 19))["available"])
        with closing(sqlite3.connect(self.catalogue.filename)) as db:
            stored = json.loads(db.execute("SELECT payload FROM products").fetchone()[0])
        self.assertEqual(stored["availableStart"], stored["seasonalStartDate"])
        self.assertEqual(stored["availableEnd"], stored["seasonalEndDate"])

    def test_publication_rejects_conflicting_dates_even_with_success_flag(self):
        with self.assertRaises(BusinessError):
            self.catalogue.publish({**self.values, "seasonalEndDate": "2027-01-01",
                                    "validationPassed": True, "certificationResult": "valid"})

    def test_publication_outside_either_season_boundary_is_unavailable(self):
        values = {**self.values, "validationPassed": True, "certificationResult": "valid"}
        for today in (date(2025, 12, 31), date(2027, 1, 1)):
            self.assertFalse(self.catalogue.publish(values, today)["available"])

    def test_correction_feedback_matches_the_form_message_key(self):
        values = {**self.values, "validationErrors": [], "certificationResult": "invalid"}
        result = self.worker.handle(self.job("request-product-correction", values))
        message = self.client.events[0]
        self.assertEqual(message[1:3], ("brfn.product.correction-requested", "test-submission-001"))
        self.assertIn("Organic certification is invalid", result["validationMessage"])
        self.assertNotIn("organicClaimed", result)

    def test_publication_confirmation_uses_submission_correlation(self):
        values = {**self.seasonal_values(), "published": True}
        result = self.worker.handle(self.job("notify-product-published", values))
        self.assertTrue(result["publicationConfirmed"])
        self.assertEqual(self.client.events[0], (
            "message", "brfn.inventory.product-listed", values["productId"],
            {"productId": values["productId"], "submissionId": values["submissionId"],
             "stockQuantity": values["stockQuantity"], "availableStart": values["seasonalStartDate"],
             "availableEnd": values["seasonalEndDate"]}, "inventory-listed-123"))
        self.assertEqual(self.client.events[1][1:3], ("brfn.product.published", "test-submission-001"))

    def test_unpublished_product_sends_no_handoff_or_confirmation(self):
        with self.assertRaises(BusinessError):
            self.worker.handle(self.job("notify-product-published"))
        self.assertFalse(self.client.events)

    def test_new_validation_errors_take_priority_over_previous_invalid_certificate(self):
        values = {**self.values, "validationErrors": ["Description is required."],
                  "certificationResult": "invalid"}
        result = self.worker.handle(self.job("request-product-correction", values))
        self.assertEqual(result["validationMessage"], "Description is required.")

    def test_producer_message_cannot_override_marketplace_control_variables(self):
        filename = Path(self.tmp.name) / "submit.json"
        filename.write_text(json.dumps({**sample(), "validationPassed": True,
                                        "certificationResult": "valid", "certificationFailures": -99}))
        correlation = producer_message(self.client, filename)
        message = self.client.events[0]
        self.assertEqual(message[1:3], ("brfn.product.submitted", correlation))
        for key in ("validationPassed", "certificationResult", "certificationFailures"):
            self.assertNotIn(key, message[3])

    def test_identical_resubmissions_have_distinct_message_ids(self):
        filename = Path(self.tmp.name) / "correct.json"
        filename.write_text(json.dumps(self.values))
        for _ in range(2):
            producer_message(self.client, filename, self.values["submissionId"])
        self.assertNotEqual(self.client.events[0][-1], self.client.events[1][-1])


class ModelContractTests(unittest.TestCase):
    def test_forms_and_bpmn_share_identifiers(self):
        ns = {"b": "http://www.omg.org/spec/BPMN/20100524/MODEL",
              "z": "http://camunda.org/schema/zeebe/1.0"}
        root = ET.parse(ROOT / "models/validation.bpmn").getroot()
        refs = {e.get("formId") for e in root.findall(".//z:formDefinition", ns)}
        forms = {json.loads(p.read_text())["id"] for p in (ROOT / "camunda/forms").glob("*.form")}
        self.assertEqual(refs, forms)
        for name in ("SubmitProductDetails", "CorrectProductDetails"):
            form = json.loads((ROOT / "camunda/forms" / (name + ".form")).read_text())
            keys = {e.get("key") for e in form["components"]}
            for key in sample():
                self.assertIn(key, keys)
        review = json.loads((ROOT / "camunda/forms/ManualCertificationReview.form").read_text())
        approved = next(e for e in review["components"] if e.get("key") == "reviewApproved")
        self.assertEqual(approved["type"], "checkbox")

    def test_counter_has_one_owner_and_caller_is_preserved(self):
        ns = {"b": "http://www.omg.org/spec/BPMN/20100524/MODEL",
              "z": "http://camunda.org/schema/zeebe/1.0"}
        root = ET.parse(ROOT / "models/validation.bpmn").getroot()
        increments = [e for e in root.findall(".//z:output", ns)
                      if e.get("target") == "certificationFailures" and "+ 1" in e.get("source", "")]
        self.assertEqual(len(increments), 1)
        call = root.find(".//b:callActivity[@id='Task_VerifyCertification']", ns)
        self.assertIsNotNone(call)
        self.assertEqual(call.find(".//z:calledElement", ns).get("processId"), "Process_ExternalCertification")
        outputs = call.findall(".//z:output", ns)
        self.assertEqual([e.get("target") for e in outputs], ["certificationResult"])


class RestContractTests(unittest.TestCase):
    def test_registry_outage_and_recovery_re_read_state_without_changing_product(self):
        from validation_worker import post_json
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "registry.json"
            state.write_text(json.dumps({"available": False, "certificates": {"BRFN-VALID-001": True}}))
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state_file=state))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{server.server_port}/verify"
            payload = {"certificateNumber": "BRFN-VALID-001"}
            try:
                with self.assertRaises(ApiError) as error:
                    post_json(url, payload)
                self.assertEqual(error.exception.status, 503)
                state.write_text(json.dumps({"available": True, "certificates": {"BRFN-VALID-001": True}}))
                self.assertEqual(post_json(url, payload), {"result": "valid"})
                state.unlink()
                with self.assertRaises(ApiError) as error:
                    post_json(url, payload)
                self.assertEqual(error.exception.status, 503)
            finally:
                server.shutdown()
                server.server_close()

    def test_mock_scenario_override_disabled_by_default(self):
        from validation_worker import post_json
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(ApiError) as error:
                post_json(f"http://127.0.0.1:{server.server_port}/verify",
                          {"certificateNumber": "UNKNOWN", "scenario": "valid"})
            self.assertEqual(error.exception.status, 400)
        finally:
            server.shutdown()
            server.server_close()

    def test_camunda_rest_paths_and_payloads_match_v2_contract(self):
        recorded = []
        class FakeGateway(BaseHTTPRequestHandler):
            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                recorded.append((self.path, data))
                response = json.dumps({"jobs": []} if self.path.endswith("activation") else {}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeGateway)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        class NoToken:
            def get(self): return ""
        try:
            client = CamundaClient(f"http://127.0.0.1:{server.server_port}", NoToken())
            job = {"jobKey": "123", "retries": 3}
            client.activate("verify-organic-cert", 2)
            client.complete(job, {"certificationResult": "valid"})
            client.throw(job, BusinessError("SERVICE_UNAVAILABLE", "mock outage"))
            client.fail(job, ValueError("technical failure"))
            client.publish("brfn.product.corrected", "submission-1", {"productName": "Carrots"}, "event-1")
            self.assertEqual([p for p, _ in recorded], [
                "/v2/jobs/activation", "/v2/jobs/123/completion", "/v2/jobs/123/error",
                "/v2/jobs/123/failure", "/v2/messages/publication"])
            self.assertEqual(recorded[0][1]["maxJobsToActivate"], 2)
            self.assertEqual(recorded[2][1]["errorCode"], "SERVICE_UNAVAILABLE")
            self.assertEqual(recorded[3][1]["retries"], 2)
            self.assertEqual(recorded[4][1]["correlationKey"], "submission-1")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
