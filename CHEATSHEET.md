# DevTrack — Interview Cheatsheet

## Run it right now (zero dependencies)
```bash
python3 run_demo.py          # start the server
python3 test_demo.py         # run all tests (in another terminal)
```

## Run with Docker (on your laptop)
```bash
docker build -t devtrack-api .
docker run -p 8000:8000 devtrack-api
# Visit: http://localhost:8000/docs
```

## Run the full stack (Docker Compose)
```bash
docker compose up -d         # start everything in background
docker compose logs -f       # follow logs
docker compose down          # stop everything
```

## Run tests
```bash
pytest tests/ -v             # run all tests
pytest tests/ --cov=app      # with coverage report
pytest tests/test_health.py  # run one file only
```

## Deploy to Kubernetes
```bash
kubectl apply -f k8s/                    # apply all manifests
kubectl get pods -n devtrack             # check pods
kubectl rollout status deployment/devtrack-api -n devtrack
kubectl rollout undo deployment/devtrack-api -n devtrack   # rollback!
kubectl logs -f deployment/devtrack-api -n devtrack
kubectl scale deployment/devtrack-api --replicas=5 -n devtrack
```

## Terraform
```bash
terraform init               # download providers, set up backend
terraform plan               # preview changes (ALWAYS run before apply)
terraform apply              # apply changes
terraform output             # show outputs
terraform destroy            # destroy everything
```

## Ansible
```bash
ansible-playbook ansible/playbook.yml -i inventory/hosts.ini --check   # dry run
ansible-playbook ansible/playbook.yml -i inventory/hosts.ini            # run it
```

---

## Top Interview Questions & Answers

**Q: What is the difference between a Pod and a Deployment?**
A Pod is a single running instance of your app. A Deployment manages a set of identical pods, handles rolling updates, and ensures the desired replica count is always maintained.

**Q: What happens when a liveness probe fails?**
Kubernetes restarts the container. If readiness probe fails, the pod is removed from the Service's load balancer but not restarted.

**Q: What is the difference between CMD and ENTRYPOINT in a Dockerfile?**
CMD provides default arguments that can be overridden at `docker run`. ENTRYPOINT sets the executable that always runs. Combining them: ENTRYPOINT is the binary, CMD is its default flags.

**Q: Why do we use multi-stage Docker builds?**
To keep production images small. Stage 1 installs build tools and compiles/installs dependencies. Stage 2 starts fresh and only copies the output — no build tools, pip cache, or dev packages in the final image.

**Q: What is Terraform state?**
A JSON file that tracks what resources Terraform has created and their current configuration. Always store it remotely (Azure Blob Storage) so it's shared across the team and locked during concurrent operations.

**Q: What is the difference between ConfigMap and Secret in Kubernetes?**
ConfigMap stores plain-text non-sensitive configuration. Secret stores base64-encoded sensitive values. In production, Secrets should be backed by Azure KeyVault or AWS Secrets Manager — never stored as plain values in a repo.

**Q: What is a Prometheus metric and what types exist?**
Counter (always increases — e.g. total requests), Gauge (can go up/down — e.g. active connections), Histogram (samples observations into buckets — e.g. request latency), Summary (similar to histogram with quantiles).

**Q: What is the Elvis operator in Groovy?**
`?:` — returns the left side if it's not null/falsy, otherwise the right side. E.g. `def tag = params.IMAGE_TAG ?: env.GIT_COMMIT`

**Q: What is an Ansible handler?**
A task that only runs when explicitly notified by another task that made a change. Handlers run once at the end of the play regardless of how many tasks notified them — prevents unnecessary restarts.

**Q: Difference between Docker Compose and Kubernetes?**
Docker Compose orchestrates multiple containers locally on a single machine. Kubernetes orchestrates containers at scale across a cluster of machines, with features like auto-scaling, self-healing, rolling updates, and service discovery.
