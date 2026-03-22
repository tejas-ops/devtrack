# test_health.py — tests for /health and /ready endpoints
#
# NAMING CONVENTION:
#   - File must start with test_  (pytest discovers it automatically)
#   - Function must start with test_
#   - Each test function tests ONE specific behaviour
#   - Names should be descriptive: test_health_returns_healthy_status
#
# WHY test the health endpoint?
#   If K8s liveness probes fail, pods restart. A broken /health endpoint
#   can bring down your entire deployment. Always test it.


def test_health_returns_200(client):
    """
    The most basic test: does the endpoint exist and return 200?
    'client' is injected by pytest from conftest.py automatically.
    """
    response = client.get("/health")                 # make GET request
    assert response.status_code == 200               # check HTTP status code
    # assert = if this is False, pytest marks the test as FAILED and shows the value


def test_health_returns_healthy_status(client):
    """Check the response body contains the right status value."""
    response = client.get("/health")
    data = response.json()                           # parse JSON body into a Python dict
    assert data["status"] == "healthy"


def test_health_includes_version(client):
    """Verify version is present — useful for confirming which build is deployed."""
    response = client.get("/health")
    data = response.json()
    assert "version" in data                         # key exists
    assert isinstance(data["version"], str)          # it's a string
    assert len(data["version"]) > 0                  # it's not empty


def test_health_includes_uptime(client):
    """Uptime should be a non-negative number."""
    response = client.get("/health")
    data = response.json()
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0


def test_readiness_probe_returns_200(client):
    """K8s readiness probe — must return 200 when ready to serve traffic."""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_root_returns_200(client):
    """Root endpoint should be reachable."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "docs" in data
