# database.py — our in-memory "database"
#
# WHY in-memory?
#   So you can run this project with ZERO external dependencies right now.
#   Later (Step 4) we'll swap this for PostgreSQL via Docker Compose — the rest
#   of the app doesn't change at all because we've isolated the DB logic here.
#
# This is the Repository Pattern: the rest of the app doesn't care HOW data
# is stored, it just calls these functions.

from typing import List, Optional
from app.models import Deployment, DeploymentCreate
from datetime import datetime, timezone


# The "database" — just a list held in memory while the app runs
_deployments: List[Deployment] = []

# Auto-increment counter (like a database sequence / IDENTITY column)
_next_id: int = 1


def get_all_deployments() -> List[Deployment]:
    """Return every deployment, newest first."""
    return list(reversed(_deployments))  # reversed() so latest shows first


def get_deployment_by_id(deployment_id: int) -> Optional[Deployment]:
    """Find a single deployment by its ID. Returns None if not found."""
    for dep in _deployments:          # loop through every record
        if dep.id == deployment_id:   # check if ID matches
            return dep                # found it — return immediately
    return None                       # not found — caller decides what to do


def create_deployment(data: DeploymentCreate) -> Deployment:
    """Save a new deployment and return the saved record (with ID + timestamp)."""
    global _next_id  # we need to modify the module-level counter

    new_deployment = Deployment(
        id          = _next_id,                          # assign next ID
        deployed_at = datetime.now(timezone.utc),        # always UTC — never local time
        **data.model_dump()                              # unpack all fields from the POST body
        # **data.model_dump() is equivalent to:
        #   app_name=data.app_name, version=data.version, ...
    )

    _deployments.append(new_deployment)  # save to our list
    _next_id += 1                        # increment counter for next record
    return new_deployment


def clear_all() -> None:
    """Wipe all records — used in tests so each test starts clean."""
    global _deployments, _next_id
    _deployments = []
    _next_id = 1
