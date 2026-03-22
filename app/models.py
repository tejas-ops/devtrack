# models.py — defines the shape of our data using Pydantic
# Pydantic automatically validates incoming JSON and gives helpful errors
# FastAPI uses these models to generate Swagger docs automatically

from pydantic import BaseModel, Field  # BaseModel = the base class for all models
from datetime import datetime          # to timestamp each deployment
from typing import Optional            # Optional means the field can be None
from enum import Enum                  # Enum = a fixed set of allowed values


# --- Enums keep values consistent (no typos like "Prod" vs "production") ---

class Environment(str, Enum):
    """Allowed deployment environments."""
    dev     = "dev"
    staging = "staging"
    prod    = "prod"


class DeploymentStatus(str, Enum):
    """Allowed deployment statuses."""
    success = "success"
    failed  = "failed"
    pending = "pending"


# --- DeploymentCreate: what the caller SENDS us (POST body) ---

class DeploymentCreate(BaseModel):
    app_name:    str         = Field(..., min_length=1, description="Name of the application")
    version:     str         = Field(..., description="Version tag e.g. v1.2.3 or git SHA")
    environment: Environment = Field(..., description="Target environment")
    status:      DeploymentStatus = Field(DeploymentStatus.pending, description="Deployment status")
    deployed_by: str         = Field(..., description="Who triggered this deployment")
    notes:       Optional[str] = Field(None, description="Optional release notes")

    # Field(...) means REQUIRED — the ... is Python's way of saying "no default, must provide"
    # Field(DeploymentStatus.pending) means OPTIONAL with a default value


# --- Deployment: the full record we STORE and RETURN ---

class Deployment(DeploymentCreate):
    """Extends DeploymentCreate by adding server-generated fields."""
    id:           int      # auto-incremented ID we assign
    deployed_at:  datetime # timestamp we set on the server — callers can't fake it

    class Config:
        # This tells Pydantic to work with ORM objects too (e.g. SQLAlchemy rows)
        from_attributes = True
