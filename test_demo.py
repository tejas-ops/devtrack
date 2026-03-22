#!/usr/bin/env python3
"""
test_demo.py — automated tests for the demo server using only stdlib.
Run WHILE the server is running in another terminal:
    Terminal 1:  python3 run_demo.py
    Terminal 2:  python3 test_demo.py

These tests map 1:1 to the pytest tests in tests/test_deployments.py.
Both do the same thing — this version just uses urllib instead of httpx.
"""

import json
import urllib.request
import urllib.error
import sys

BASE = "http://localhost:8000"
PASS = "✅"
FAIL = "❌"
results = []


# ─── Test helper ────────────────────────────────────────────────────────────

def http(method, path, body=None, params=None):
    """
    Make an HTTP request and return (status_code, response_body_dict).
    This is what httpx/requests does under the hood.
    """
    url = BASE + path
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url += "?" + qs

    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def check(name, condition, got=None):
    """Assert helper — records pass/fail."""
    if condition:
        print(f"  {PASS}  {name}")
        results.append(True)
    else:
        print(f"  {FAIL}  {name}  (got: {got})")
        results.append(False)


# ─── Tests ──────────────────────────────────────────────────────────────────

def test_health():
    print("\n📋  Health endpoint tests")
    status, body = http("GET", "/health")
    check("GET /health → 200",            status == 200, status)
    check("body has 'status' key",        "status" in body, body)
    check("status is 'healthy'",          body.get("status") == "healthy", body.get("status"))
    check("body has 'uptime_seconds'",    "uptime_seconds" in body, body)
    check("uptime_seconds is a number",   isinstance(body.get("uptime_seconds"), (int, float)))


def test_create_deployment():
    print("\n📋  Create deployment tests")

    # ── Happy path ──
    status, body = http("POST", "/deployments", {
        "app_name":    "payment-service",
        "version":     "v2.1.0",
        "environment": "staging",
        "deployed_by": "tejas",
        "notes":       "Fix for JIRA-123"
    })
    check("POST /deployments → 201",           status == 201, status)
    check("response has 'id'",                 "id" in body, body)
    check("response has 'deployed_at'",        "deployed_at" in body, body)
    check("app_name matches",                  body.get("app_name") == "payment-service")
    check("version matches",                   body.get("version") == "v2.1.0")
    check("default status is 'pending'",       body.get("status") == "pending", body.get("status"))

    # ── Validation: missing required field ──
    status2, body2 = http("POST", "/deployments", {
        "version": "v1.0.0",    # missing app_name, environment, deployed_by
    })
    check("missing required field → 422",  status2 == 422, status2)
    check("error body has 'detail'",       "detail" in body2, body2)

    # ── Validation: invalid environment ──
    status3, body3 = http("POST", "/deployments", {
        "app_name":    "test-app",
        "version":     "v1.0.0",
        "environment": "production",   # not in allowed list
        "deployed_by": "tejas",
    })
    check("invalid environment → 422",  status3 == 422, status3)


def test_list_deployments():
    print("\n📋  List deployments tests")
    # First create some deployments
    for i in range(3):
        http("POST", "/deployments", {
            "app_name":    f"app-{i}",
            "version":     f"v1.{i}.0",
            "environment": "dev",
            "deployed_by": "tejas",
        })

    status, body = http("GET", "/deployments")
    check("GET /deployments → 200",     status == 200, status)
    check("returns a list",             isinstance(body, list), type(body).__name__)
    check("list has items",             len(body) > 0, len(body))
    check("first item has 'id'",        "id" in body[0], body[0] if body else None)


def test_get_by_id():
    print("\n📋  Get by ID tests")

    # Create a deployment
    _, created = http("POST", "/deployments", {
        "app_name":    "order-service",
        "version":     "v3.0.0",
        "environment": "prod",
        "deployed_by": "tejas",
    })
    dep_id = created["id"]

    # Fetch it back
    status, body = http("GET", f"/deployments/{dep_id}")
    check(f"GET /deployments/{dep_id} → 200",  status == 200, status)
    check("correct record returned",            body.get("id") == dep_id)
    check("app_name matches",                   body.get("app_name") == "order-service")

    # Fetch non-existent
    status2, body2 = http("GET", "/deployments/99999")
    check("GET /deployments/99999 → 404",  status2 == 404, status2)
    check("error has 'detail'",            "detail" in body2)

    # Fetch with non-integer ID
    status3, _ = http("GET", "/deployments/abc")
    check("GET /deployments/abc → 400",  status3 == 400, status3)


def test_update_status():
    print("\n📋  Update status tests")

    # Create a pending deployment
    _, created = http("POST", "/deployments", {
        "app_name":    "notification-service",
        "version":     "v1.5.0",
        "environment": "staging",
        "deployed_by": "tejas",
    })
    dep_id = created["id"]

    # Update to success
    status, body = http("PATCH", f"/deployments/{dep_id}/status",
                        params={"new_status": "success"})
    check("PATCH status → 200",           status == 200, status)
    check("status updated to 'success'",  body.get("status") == "success", body.get("status"))

    # Update to failed
    status2, body2 = http("PATCH", f"/deployments/{dep_id}/status",
                          params={"new_status": "failed"})
    check("PATCH to 'failed' → 200",   status2 == 200, status2)
    check("status updated to 'failed'", body2.get("status") == "failed")

    # Invalid status
    status3, _ = http("PATCH", f"/deployments/{dep_id}/status",
                      params={"new_status": "running"})
    check("invalid status → 422",  status3 == 422, status3)


# ─── Run all tests ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  DevTrack API — Test Suite")
    print("=" * 50)

    # Quick connectivity check
    try:
        http("GET", "/health")
    except Exception:
        print(f"\n{FAIL} Cannot reach {BASE}")
        print("   Make sure the server is running:  python3 run_demo.py")
        sys.exit(1)

    test_health()
    test_create_deployment()
    test_list_deployments()
    test_get_by_id()
    test_update_status()

    # Summary
    total = len(results)
    passed = sum(results)
    failed = total - passed
    print(f"\n{'=' * 50}")
    print(f"  {PASS} {passed} passed   {FAIL if failed else ''} {failed if failed else ''} failed   (total: {total})")
    print("=" * 50)
    sys.exit(0 if failed == 0 else 1)
