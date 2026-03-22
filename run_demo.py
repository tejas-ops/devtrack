#!/usr/bin/env python3
"""
run_demo.py — zero-dependency version of DevTrack
Runs with only Python's standard library.
Teaches the SAME concepts as FastAPI: routing, JSON, HTTP status codes, validation.

Start it with:  python3 run_demo.py
Then test with: python3 test_demo.py
"""

import json                          # parse/produce JSON
import http.server                   # built-in HTTP server
import time                          # uptime calculation
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs  # parse URL paths and query strings


# ─────────────────────────────────────────────
# "DATABASE" — same concept as app/database.py
# ─────────────────────────────────────────────
_deployments = []    # in-memory list — our "database"
_next_id     = 1     # auto-increment counter
_start_time  = time.time()

ALLOWED_ENVS    = {"dev", "staging", "prod"}
ALLOWED_STATUSES = {"success", "failed", "pending"}


def db_get_all():
    return list(reversed(_deployments))   # newest first


def db_get_by_id(dep_id):
    for d in _deployments:
        if d["id"] == dep_id:
            return d
    return None


def db_create(data):
    global _next_id
    record = {
        "id":          _next_id,
        "deployed_at": datetime.now(timezone.utc).isoformat(),
        **data    # unpack all fields from the request body
    }
    _deployments.append(record)
    _next_id += 1
    return record


def db_update_status(dep_id, new_status):
    for i, d in enumerate(_deployments):
        if d["id"] == dep_id:
            _deployments[i] = {**d, "status": new_status}
            return _deployments[i]
    return None


# ─────────────────────────────────────────────
# REQUEST HANDLER
# ─────────────────────────────────────────────

class DevTrackHandler(http.server.BaseHTTPRequestHandler):
    """
    This class handles every incoming HTTP request.
    In FastAPI, the framework does this for you with @app.get(), @app.post() etc.
    Here we do it manually so you can SEE what's happening underneath.
    """

    def log_message(self, format, *args):
        """Override default logging to make it cleaner."""
        print(f"  [{self.command}] {self.path} → {args[1] if len(args) > 1 else ''}")

    # ── Helpers ──────────────────────────────

    def send_json(self, data, status=200):
        """Send a JSON response — the equivalent of FastAPI's JSONResponse."""
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status, detail):
        """Send a {"detail": "..."} error — same format as FastAPI's HTTPException."""
        self.send_json({"detail": detail}, status)

    def read_body(self):
        """Read and parse the JSON request body."""
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def get_path_parts(self):
        """
        Split URL path into parts. '/deployments/42' → ['deployments', '42']
        IMPORTANT: self.path includes the query string e.g. /deployments/5/status?new_status=success
        We MUST parse it first to separate path from query string, otherwise
        'status?new_status=success' would become one part and the route match fails.
        """
        pure_path = urlparse(self.path).path   # strips ?query from path
        return [p for p in pure_path.split("/") if p]

    def validate_deployment_body(self, body):
        """
        Manual validation — FastAPI+Pydantic does this automatically.
        Returns (error_message, None) if invalid, or (None, cleaned_data) if valid.
        """
        required = ["app_name", "version", "environment", "deployed_by"]
        for field in required:
            if field not in body or not body[field]:
                return f"Missing required field: '{field}'", None

        env = body.get("environment", "")
        if env not in ALLOWED_ENVS:
            return f"environment must be one of {ALLOWED_ENVS}", None

        status = body.get("status", "pending")
        if status not in ALLOWED_STATUSES:
            return f"status must be one of {ALLOWED_STATUSES}", None

        return None, {
            "app_name":    str(body["app_name"]),
            "version":     str(body["version"]),
            "environment": env,
            "status":      status,
            "deployed_by": str(body["deployed_by"]),
            "notes":       body.get("notes"),   # optional field
        }

    # ── Route Dispatcher ─────────────────────

    def do_GET(self):
        """Handle all GET requests — dispatches to the right handler."""
        parts = self.get_path_parts()

        # GET /  →  API info
        if not parts:
            self.send_json({"service": "DevTrack API", "docs": "see README", "health": "/health"})

        # GET /health
        elif parts == ["health"]:
            uptime = round(time.time() - _start_time, 2)
            self.send_json({"status": "healthy", "uptime_seconds": uptime, "version": "1.0.0"})

        # GET /ready
        elif parts == ["ready"]:
            self.send_json({"status": "ready"})

        # GET /deployments
        elif parts == ["deployments"]:
            self.send_json(db_get_all())

        # GET /deployments/{id}
        elif len(parts) == 2 and parts[0] == "deployments":
            try:
                dep_id = int(parts[1])
            except ValueError:
                self.send_error_json(400, f"Deployment ID must be an integer, got: '{parts[1]}'")
                return
            dep = db_get_by_id(dep_id)
            if dep is None:
                self.send_error_json(404, f"Deployment {dep_id} not found")
            else:
                self.send_json(dep)

        else:
            self.send_error_json(404, f"Route not found: GET {self.path}")

    def do_POST(self):
        """Handle all POST requests."""
        parts = self.get_path_parts()

        # POST /deployments
        if parts == ["deployments"]:
            body = self.read_body()
            if body is None:
                self.send_error_json(400, "Invalid JSON body")
                return

            error, data = self.validate_deployment_body(body)
            if error:
                self.send_error_json(422, error)   # 422 = Unprocessable Entity (FastAPI's default)
                return

            record = db_create(data)
            self.send_json(record, 201)   # 201 Created

        else:
            self.send_error_json(404, f"Route not found: POST {self.path}")

    def do_PATCH(self):
        """Handle PATCH /deployments/{id}/status?new_status=success"""
        parts = self.get_path_parts()

        # PATCH /deployments/{id}/status
        if len(parts) == 3 and parts[0] == "deployments" and parts[2] == "status":
            try:
                dep_id = int(parts[1])
            except ValueError:
                self.send_error_json(400, "Deployment ID must be an integer")
                return

            # Parse query string:  ?new_status=success
            qs = parse_qs(urlparse(self.path).query)
            new_status = qs.get("new_status", [None])[0]
            if new_status not in ALLOWED_STATUSES:
                self.send_error_json(422, f"new_status must be one of {ALLOWED_STATUSES}")
                return

            updated = db_update_status(dep_id, new_status)
            if updated is None:
                self.send_error_json(404, f"Deployment {dep_id} not found")
            else:
                self.send_json(updated)

        else:
            self.send_error_json(404, f"Route not found: PATCH {self.path}")


# ─────────────────────────────────────────────
# START THE SERVER
# ─────────────────────────────────────────────

if __name__ == "__main__":
    PORT = 8000
    server = http.server.HTTPServer(("0.0.0.0", PORT), DevTrackHandler)
    print(f"""
╔══════════════════════════════════════════════╗
║         DevTrack API — running!              ║
╠══════════════════════════════════════════════╣
║  http://localhost:{PORT}/              → root  ║
║  http://localhost:{PORT}/health        → health║
║  http://localhost:{PORT}/deployments   → list  ║
╚══════════════════════════════════════════════╝
  Press Ctrl+C to stop.
""")
    try:
        server.serve_forever()   # blocks here, handling requests in a loop
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
