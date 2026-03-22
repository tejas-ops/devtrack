# ═══════════════════════════════════════════════════════════════
# Dockerfile — packaging DevTrack into a container image
#
# INTERVIEW MUST-KNOWS:
#   1. Multi-stage builds → smaller, more secure production images
#   2. Non-root user     → security: containers should NOT run as root
#   3. Layer caching     → copy requirements BEFORE source code
#   4. EXPOSE vs -p      → EXPOSE is documentation, -p actually maps the port
#   5. CMD vs ENTRYPOINT → CMD can be overridden, ENTRYPOINT cannot
# ═══════════════════════════════════════════════════════════════


# ─── STAGE 1: Build stage ─────────────────────────────────────────────────
# We install ALL dependencies (including build tools) here.
# This stage is DISCARDED after building — it never reaches production.
# Result: our final image doesn't carry build tools (gcc, pip cache, etc.)

FROM python:3.11-slim AS builder
# python:3.11-slim = official Python image based on Debian (without extras)
# AS builder        = name this stage so we can reference it in the next stage

# Set working directory inside the container
# All subsequent commands run from /build
WORKDIR /build

# ── Layer caching trick (CRITICAL for interview) ──
# Docker builds in layers. If a layer hasn't changed, it uses the CACHED version.
# requirements.txt changes RARELY, source code changes OFTEN.
# By copying requirements FIRST and source SECOND:
#   → pip install is cached unless requirements.txt changes
#   → only the COPY . . layer re-runs when you change a .py file
#   → builds go from 60s to 5s in CI/CD pipelines

COPY requirements.txt .
RUN pip install --no-cache-dir --target=/build/packages -r requirements.txt
# --no-cache-dir        = don't cache pip downloads (saves image space)
# --target=/build/packages = install to a specific folder we'll copy to stage 2


# ─── STAGE 2: Production stage ────────────────────────────────────────────
# This is the FINAL image that gets pushed to your registry and deployed.
# It starts FRESH from a clean base — no build tools, no pip cache.

FROM python:3.11-slim AS production

# Security: create a non-root user
# Running as root inside a container = if the container is compromised,
# the attacker has root privileges. Non-root = much more limited blast radius.
RUN groupadd --gid 1001 appgroup && \
    useradd  --uid 1001 --gid appgroup --no-create-home appuser
# --gid / --uid: use specific IDs (not random) for consistency across deployments

WORKDIR /app

# Copy ONLY the installed packages from stage 1 (not the build tools)
COPY --from=builder /build/packages /usr/local/lib/python3.11/site-packages/

# Copy the application source code
COPY app/ ./app/

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
# PYTHONDONTWRITEBYTECODE=1 → don't create .pyc files (not needed in containers)

ENV PYTHONUNBUFFERED=1
# PYTHONUNBUFFERED=1 → print() and logging output immediately (not buffered)
#                     → without this, logs might not appear in docker logs / K8s

ENV PORT=8000
# Store the port as a variable so it's easy to override

# Switch to non-root user BEFORE exposing port and running app
USER appuser

# EXPOSE tells Docker (and humans reading this file) which port the app uses.
# It does NOT actually publish the port — that's done with docker run -p 8000:8000
# Kubernetes uses this for documentation / some tooling picks it up automatically
EXPOSE 8000

# HEALTHCHECK: Docker will run this command every 30s
# If it fails 3 times in a row, Docker marks the container as "unhealthy"
# Kubernetes can also use this alongside its own liveness probes
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# CMD = the default command when the container starts
# Using array form (not string form) → avoids shell interpretation issues
# uvicorn = ASGI server that runs our FastAPI app
CMD ["uvicorn", "app.main:app",
     "--host", "0.0.0.0",
     "--port", "8000",
     "--workers", "2"]
# --host 0.0.0.0 → listen on ALL interfaces (not just localhost)
#                  without this, the app is unreachable from outside the container
# --workers 2    → 2 worker processes = handle 2 requests simultaneously
#                  in production: workers = (2 × CPU cores) + 1  is a common rule
