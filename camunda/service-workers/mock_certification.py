"""Local simulated certification registry; no official certification API is used."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import time


def make_handler(allow_scenarios=False, timeout_seconds=60, state_file=None):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/verify":
                self.reply(404, {"error": "Not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 16384:
                    raise ValueError
                request = json.loads(self.rfile.read(length))
                if not isinstance(request, dict):
                    raise ValueError
            except (ValueError, json.JSONDecodeError):
                self.reply(400, {"error": "Expected a JSON verification request"})
                return
            state = {"available": True, "certificates": {"BRFN-VALID-001": True}}
            if state_file:
                try:
                    state = json.loads(Path(state_file).read_text())
                    if state.get("available") is not True or not isinstance(state.get("certificates"), dict):
                        raise ValueError
                except (OSError, ValueError, AttributeError):
                    self.reply(503, {"result": "unavailable"})
                    return
            scenario = request.get("scenario")
            if scenario is not None:
                if not allow_scenarios or scenario not in ("valid", "invalid", "unavailable", "error", "timeout"):
                    self.reply(400, {"error": "Scenario override is disabled or unknown"})
                    return
                if scenario == "unavailable":
                    self.reply(503, {"result": "unavailable"})
                    return
                if scenario == "error":
                    self.reply(200, {"errorCode": "SERVICE_UNAVAILABLE"})
                    return
                if scenario == "timeout":
                    time.sleep(timeout_seconds)
                    self.reply(503, {"result": "unavailable"})
                    return
                self.reply(200, {"result": scenario})
                return
            # Explicit local fixture lookup. Missing/unknown certificates are invalid.
            valid = state["certificates"].get(request.get("certificateNumber")) is True
            self.reply(200, {"result": "valid" if valid else "invalid"})

        def reply(self, status, payload):
            try:
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass  # A caller or parent timeout may already have closed the request.

        def log_message(self, *_):
            pass
    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--allow-scenarios", action="store_true")
    parser.add_argument("--state-file", help="Local registry JSON re-read for each request")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port),
                                 make_handler(args.allow_scenarios, state_file=args.state_file))
    print(f"Simulated verifier listening on http://127.0.0.1:{args.port}/verify", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
