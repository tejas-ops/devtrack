# test_deployments.py — tests for /deployments endpoints
#
# TEST CATEGORIES we cover:
#   1. Happy path  — the normal, correct usage
#   2. Validation  — what happens with bad input
#   3. Not found   — 404 scenarios
#   4. Edge cases  — boundary conditions
#
# This mirrors real interview questions:
#   "How do you test an API endpoint?"
#   "What's the difference between unit and integration tests?"
#   "How do you ensure tests don't affect each other?"

import pytest


# ─── CREATE DEPLOYMENT ───────────────────────────────────────────────────────

class TestCreateDeployment:
    """
    Grouping related tests in a class keeps things organised.
    pytest discovers test classes automatically (no base class needed).
    """

    def test_create_returns_201(self, client, sample_deployment_payload):
        """201 Created is the correct status for a new resource."""
        response = client.post("/deployments/", json=sample_deployment_payload)
        assert response.status_code == 201

    def test_create_returns_deployment_with_id(self, client, sample_deployment_payload):
        """Server must assign an ID — the client can't choose it."""
        response = client.post("/deployments/", json=sample_deployment_payload)
        data = response.json()
        assert "id" in data
        assert isinstance(data["id"], int)
        assert data["id"] >= 1

    def test_create_sets_deployed_at_timestamp(self, client, sample_deployment_payload):
        """Server must set the timestamp — the client can't fake it."""
        response = client.post("/deployments/", json=sample_deployment_payload)
        data = response.json()
        assert "deployed_at" in data
        assert data["deployed_at"] is not None

    def test_create_defaults_status_to_pending(self, client, sample_deployment_payload):
        """When no status is provided, it should default to 'pending'."""
        # Remove status from payload if it's there
        payload = {k: v for k, v in sample_deployment_payload.items() if k != "status"}
        response = client.post("/deployments/", json=payload)
        assert response.json()["status"] == "pending"

    def test_create_accepts_explicit_status(self, client, sample_deployment_payload):
        """Caller can explicitly set status to 'success'."""
        payload = {**sample_deployment_payload, "status": "success"}
        response = client.post("/deployments/", json=payload)
        assert response.json()["status"] == "success"

    def test_create_missing_app_name_returns_422(self, client):
        """422 = Unprocessable Entity — validation failed."""
        response = client.post("/deployments/", json={
            "version":     "v1.0.0",
            "environment": "dev",
            "deployed_by": "tejas",
        })
        assert response.status_code == 422

    def test_create_missing_version_returns_422(self, client):
        response = client.post("/deployments/", json={
            "app_name":    "my-app",
            "environment": "dev",
            "deployed_by": "tejas",
        })
        assert response.status_code == 422

    def test_create_invalid_environment_returns_422(self, client):
        """'production' is not a valid enum value — only dev/staging/prod are."""
        response = client.post("/deployments/", json={
            "app_name":    "my-app",
            "version":     "v1.0.0",
            "environment": "production",   # invalid!
            "deployed_by": "tejas",
        })
        assert response.status_code == 422

    def test_create_invalid_status_returns_422(self, client):
        response = client.post("/deployments/", json={
            "app_name":    "my-app",
            "version":     "v1.0.0",
            "environment": "dev",
            "deployed_by": "tejas",
            "status":      "running",     # invalid!
        })
        assert response.status_code == 422

    def test_ids_auto_increment(self, client, sample_deployment_payload):
        """Each new deployment gets the next sequential ID."""
        r1 = client.post("/deployments/", json=sample_deployment_payload)
        r2 = client.post("/deployments/", json=sample_deployment_payload)
        id1 = r1.json()["id"]
        id2 = r2.json()["id"]
        assert id2 == id1 + 1


# ─── LIST DEPLOYMENTS ────────────────────────────────────────────────────────

class TestListDeployments:

    def test_list_returns_empty_initially(self, client):
        """Fresh start — no deployments yet — list should be empty."""
        response = client.get("/deployments/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_all_deployments(self, client, sample_deployment_payload):
        """After creating 3, list should return 3."""
        for _ in range(3):
            client.post("/deployments/", json=sample_deployment_payload)
        response = client.get("/deployments/")
        assert len(response.json()) == 3

    def test_list_newest_first(self, client):
        """Newest deployment should appear first in the list (descending order)."""
        r1 = client.post("/deployments/", json={
            "app_name": "first-app", "version": "v1", "environment": "dev", "deployed_by": "a"
        })
        r2 = client.post("/deployments/", json={
            "app_name": "second-app", "version": "v1", "environment": "dev", "deployed_by": "b"
        })
        items = client.get("/deployments/").json()
        # The last created item should appear first
        assert items[0]["id"] == r2.json()["id"]
        assert items[1]["id"] == r1.json()["id"]


# ─── GET BY ID ───────────────────────────────────────────────────────────────

class TestGetDeploymentById:

    def test_get_existing_returns_200(self, client, sample_deployment_payload):
        created_id = client.post("/deployments/", json=sample_deployment_payload).json()["id"]
        response = client.get(f"/deployments/{created_id}")
        assert response.status_code == 200

    def test_get_existing_returns_correct_record(self, client, sample_deployment_payload):
        """Verify the returned record matches what was created."""
        created = client.post("/deployments/", json=sample_deployment_payload).json()
        fetched = client.get(f"/deployments/{created['id']}").json()
        assert fetched["id"]       == created["id"]
        assert fetched["app_name"] == sample_deployment_payload["app_name"]
        assert fetched["version"]  == sample_deployment_payload["version"]

    def test_get_non_existent_returns_404(self, client):
        """Requesting an ID that doesn't exist should return 404."""
        response = client.get("/deployments/99999")
        assert response.status_code == 404
        assert "detail" in response.json()   # FastAPI standard error format


# ─── UPDATE STATUS ───────────────────────────────────────────────────────────

class TestUpdateStatus:

    def test_update_pending_to_success(self, client, sample_deployment_payload):
        """Simulate CI/CD marking a deployment as succeeded."""
        dep_id = client.post("/deployments/", json=sample_deployment_payload).json()["id"]
        response = client.patch(f"/deployments/{dep_id}/status?new_status=success")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_update_to_failed(self, client, sample_deployment_payload):
        """Simulate CI/CD marking a deployment as failed."""
        dep_id = client.post("/deployments/", json=sample_deployment_payload).json()["id"]
        response = client.patch(f"/deployments/{dep_id}/status?new_status=failed")
        assert response.json()["status"] == "failed"

    def test_update_non_existent_returns_404(self, client):
        response = client.patch("/deployments/99999/status?new_status=success")
        assert response.status_code == 404

    def test_update_invalid_status_returns_422(self, client, sample_deployment_payload):
        dep_id = client.post("/deployments/", json=sample_deployment_payload).json()["id"]
        response = client.patch(f"/deployments/{dep_id}/status?new_status=running")
        assert response.status_code == 422
