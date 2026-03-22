# health.py — the /health endpoint
#
# WHY have a health endpoint?
#   Kubernetes uses it for Liveness and Readiness Probes.
#   If /health returns non-200, K8s restarts the pod.
#   Load balancers use it to route traffic only to healthy pods.
#   This is one of the MOST common interview questions about K8s.

from fastapi import APIRouter   # APIRouter lets us split routes across files
from datetime import datetime, timezone

# Create a router — we'll register this on the main app in main.py
router = APIRouter()

# Record when the app started (so we can report uptime)
_start_time = datetime.now(timezone.utc)

APP_VERSION = "1.0.0"   # In a real pipeline this comes from a git tag / env var


@router.get("/health")
def health_check():
    """
    Liveness probe endpoint.
    Returns 200 OK when the app is running.
    K8s checks this every few seconds.
    """
    now = datetime.now(timezone.utc)
    uptime_seconds = (now - _start_time).total_seconds()

    return {
        "status":          "healthy",
        "version":         APP_VERSION,
        "uptime_seconds":  round(uptime_seconds, 2),
        "timestamp":       now.isoformat(),
    }
    # FastAPI automatically converts this dict to JSON and sets Content-Type: application/json


@router.get("/ready")
def readiness_check():
    """
    Readiness probe endpoint.
    Returns 200 only when the app is READY to serve traffic.
    In a real app you'd also check: can we reach the DB? can we reach Redis?
    """
    return {"status": "ready"}
