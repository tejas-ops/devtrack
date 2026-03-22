# deployments.py — all /deployments endpoints
#
# REST API design used here:
#   GET    /deployments        → list all
#   POST   /deployments        → create new
#   GET    /deployments/{id}   → get one
#   PATCH  /deployments/{id}   → update status (e.g. pending → success)
#
# This pattern is standard REST — interviewers WILL ask you to explain it.

from fastapi import APIRouter, HTTPException, status
# HTTPException  → return proper HTTP error codes (404, 400, etc.)
# status         → named constants like status.HTTP_201_CREATED (better than magic numbers)

from typing import List
from app.models import Deployment, DeploymentCreate, DeploymentStatus
from app import database  # import our database module

router = APIRouter(prefix="/deployments", tags=["deployments"])
# prefix="/deployments" → every route in this file automatically starts with /deployments
# tags=["deployments"]  → groups these routes together in Swagger UI (/docs)


@router.get("/", response_model=List[Deployment])
def list_deployments():
    """
    GET /deployments — return all deployments (newest first).
    response_model=List[Deployment] tells FastAPI:
      1. Validate the return value matches this type
      2. Show this schema in the Swagger docs
      3. Strip out any extra fields (security: never accidentally leak internal fields)
    """
    return database.get_all_deployments()


@router.post("/", response_model=Deployment, status_code=status.HTTP_201_CREATED)
def create_deployment(payload: DeploymentCreate):
    """
    POST /deployments — log a new deployment.
    status_code=201 → "Created" is more accurate than 200 "OK" for new resources.
    FastAPI reads the JSON body and validates it against DeploymentCreate automatically.
    If validation fails (e.g. missing field), it returns 422 Unprocessable Entity.
    """
    return database.create_deployment(payload)


@router.get("/{deployment_id}", response_model=Deployment)
def get_deployment(deployment_id: int):
    """
    GET /deployments/42 — fetch a single deployment by ID.
    FastAPI parses {deployment_id} from the URL and passes it as a Python int.
    If you send /deployments/abc it automatically returns 422 (not an int).
    """
    dep = database.get_deployment_by_id(deployment_id)
    if dep is None:
        # Raise HTTPException → FastAPI catches it and returns {"detail": "..."} JSON
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found"
        )
    return dep


@router.patch("/{deployment_id}/status", response_model=Deployment)
def update_status(deployment_id: int, new_status: DeploymentStatus):
    """
    PATCH /deployments/42/status?new_status=success
    Updates just the status field — used by your CI/CD pipeline to mark
    a deployment as success or failed after the deploy job completes.
    """
    dep = database.get_deployment_by_id(deployment_id)
    if dep is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found"
        )
    # Pydantic models are immutable by default — we use model_copy to update
    updated = dep.model_copy(update={"status": new_status})

    # Find and replace in our list
    all_deps = database._deployments
    for i, d in enumerate(all_deps):
        if d.id == deployment_id:
            all_deps[i] = updated
            break

    return updated
