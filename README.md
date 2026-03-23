# DevTrack API

A deployment tracker API built with FastAPI — designed as a hands-on DevOps learning project covering the full stack: local dev → testing → Docker → CI/CD → Kubernetes → monitoring → IaC.

## What it does

DevTrack lets you log and track deployments across environments. Think of it as a lightweight internal tool your CI/CD pipeline calls to record every deploy — who deployed what, to which environment, and whether it succeeded.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | API info |
| `GET` | `/health` | Liveness check |
| `GET` | `/ready` | Readiness check |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/deployments` | List all deployments |
| `POST` | `/deployments` | Log a new deployment |
| `GET` | `/deployments/{id}` | Get a single deployment |
| `PATCH` | `/deployments/{id}/status` | Update deployment status |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| Testing | pytest + httpx |
| Containers | Docker (multi-stage build) |
| Orchestration | Kubernetes (AKS-ready manifests) |
| CI/CD | GitHub Actions |
| IaC | Terraform |
| Config mgmt | Ansible |
| Monitoring | Prometheus + Grafana |

---

## Phase 1 — Run locally

### Prerequisites
- Python 3.11+

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/devtrack.git
cd devtrack

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload
```

The API is now running at `http://localhost:8000`.

### Explore the API

- **Swagger UI** (interactive): `http://localhost:8000/docs`
- **ReDoc** (readable): `http://localhost:8000/redoc`
- **Prometheus metrics**: `http://localhost:8000/metrics`

### Try it with curl

```bash
# Create a deployment
curl -X POST http://localhost:8000/deployments \
  -H "Content-Type: application/json" \
  -d '{"service": "auth-service", "environment": "staging", "version": "v1.2.3", "deployed_by": "tejas"}'

# List all deployments
curl http://localhost:8000/deployments

# Update status to success
curl -X PATCH "http://localhost:8000/deployments/1/status?new_status=success"
```

---

## Phase 2 — Run tests

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=term-missing

# Run a single test file
pytest tests/test_deployments.py -v
```

---

## Phase 3 — Docker

```bash
# Build the image
docker build -t devtrack-api .

# Run the container
docker run -p 8000:8000 devtrack-api

# Visit http://localhost:8000/docs
```

---

## Phase 5 — Kubernetes

```bash
# Apply all manifests
kubectl apply -f k8s/

# Check pod status
kubectl get pods -n devtrack

# Watch a rolling update
kubectl rollout status deployment/devtrack-api -n devtrack

# Rollback if something goes wrong
kubectl rollout undo deployment/devtrack-api -n devtrack

# Scale manually
kubectl scale deployment/devtrack-api --replicas=5 -n devtrack
```

---

## Phase 7 — Terraform

```bash
cd terraform/

terraform init      # download providers, set up backend
terraform plan      # preview what will be created (always run before apply)
terraform apply     # create the infrastructure
terraform output    # show output values (e.g. AKS cluster name)
terraform destroy   # tear everything down
```

---

## Phase 8 — Ansible

```bash
# Dry run (no changes made)
ansible-playbook ansible/playbook.yml -i inventory/hosts.ini --check

# Apply
ansible-playbook ansible/playbook.yml -i inventory/hosts.ini
```

---

## Project Structure

```
devtrack/
├── app/
│   ├── main.py              # FastAPI app, middleware, Prometheus metrics
│   ├── models.py            # Pydantic models (Deployment, DeploymentCreate)
│   ├── database.py          # In-memory store (swap for Postgres in production)
│   └── routes/
│       ├── health.py        # /health and /ready endpoints
│       └── deployments.py   # CRUD endpoints for deployments
├── tests/
│   ├── conftest.py          # Shared pytest fixtures
│   ├── test_health.py       # Health endpoint tests
│   └── test_deployments.py  # Deployment CRUD tests
├── k8s/                     # Kubernetes manifests
├── terraform/               # Azure infrastructure as code
├── ansible/                 # Configuration management playbook
├── Dockerfile               # Multi-stage Docker build
├── requirements.txt
└── CHEATSHEET.md            # Quick commands + interview Q&A
```

---

## Learning Roadmap

| Phase | Topic | Skills Covered |
|-------|-------|----------------|
| 1 | Local dev + API design | FastAPI, REST, Pydantic |
| 2 | Testing | pytest, httpx, coverage |
| 3 | Docker | Multi-stage builds, layer caching |
| 4 | CI/CD | GitHub Actions, automated tests + image builds |
| 5 | Kubernetes | Deployments, HPA, rolling updates, rollbacks |
| 6 | Monitoring | Prometheus, Grafana dashboards |
| 7 | Terraform | Azure IaC, remote state |
| 8 | Ansible | Configuration management, idempotency |
