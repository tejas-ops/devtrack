# main.py — the FastAPI application entry point
#
# This is the file uvicorn runs. Think of it like the "front door" of the app.
# It:
#   1. Creates the FastAPI app instance
#   2. Registers all routers (our route files)
#   3. Adds middleware (CORS, logging)
#   4. Exposes Prometheus metrics

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware  # allows browsers/other services to call our API
from prometheus_client import Counter, Histogram, make_asgi_app
import time

from app.routes import health, deployments  # import our route modules


# --- Create the FastAPI application ---
app = FastAPI(
    title       = "DevTrack API",
    description = "Track deployments across environments — built to learn DevOps end-to-end.",
    version     = "1.0.0",
    docs_url    = "/docs",    # Swagger UI lives here — visit http://localhost:8000/docs
    redoc_url   = "/redoc",   # ReDoc alternative UI
)


# --- CORS Middleware ---
# CORS = Cross-Origin Resource Sharing
# Without this, browsers block requests from different domains (e.g. your React frontend → this API)
app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],   # In production: list specific domains e.g. ["https://myapp.com"]
    allow_methods  = ["*"],   # GET, POST, PATCH, DELETE, etc.
    allow_headers  = ["*"],   # Authorization, Content-Type, etc.
)


# --- Prometheus Metrics ---
# Prometheus "scrapes" the /metrics endpoint every 15s and stores the data
# Grafana reads from Prometheus to draw dashboards

REQUEST_COUNT = Counter(
    "devtrack_request_count",          # metric name (must be unique)
    "Total number of HTTP requests",   # human-readable description
    ["method", "endpoint", "status"]   # labels — lets you filter by method/route/status in Grafana
)

REQUEST_LATENCY = Histogram(
    "devtrack_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

# Mount the Prometheus metrics endpoint at /metrics
# make_asgi_app() creates a mini ASGI app that serves all registered metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# --- Middleware to record metrics for EVERY request ---
@app.middleware("http")
async def record_metrics(request: Request, call_next):
    """
    This runs BEFORE and AFTER every single HTTP request.
    WHY middleware? So we don't have to add timing code to every route.
    This is the same idea as a decorator but for HTTP requests.
    """
    start = time.time()

    response = await call_next(request)  # await = let FastAPI process the request normally

    duration = time.time() - start

    # Record the metrics with labels
    REQUEST_COUNT.labels(
        method   = request.method,              # GET, POST, etc.
        endpoint = request.url.path,            # /deployments, /health, etc.
        status   = response.status_code         # 200, 201, 404, etc.
    ).inc()  # .inc() = increment the counter by 1

    REQUEST_LATENCY.labels(
        method   = request.method,
        endpoint = request.url.path
    ).observe(duration)  # .observe() = add this value to the histogram

    return response


# --- Register Routers ---
# include_router plugs the routes from each file into the main app
app.include_router(health.router)                          # /health, /ready
app.include_router(deployments.router)                     # /deployments/*


# --- Root endpoint ---
@app.get("/")
def root():
    """API info — useful for quickly checking the service is up."""
    return {
        "service": "DevTrack API",
        "version": "1.0.0",
        "docs":    "/docs",
        "health":  "/health",
        "metrics": "/metrics",
    }
