import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Ensure both backend and project root are in sys.path
_current_dir = Path(__file__).resolve().parent
_backend_dir = _current_dir.parent
_project_root = _backend_dir.parent
for _p in [str(_backend_dir), str(_project_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.core.config import settings
from app.core.logging import logger
from app.api.v1.router import api_router
from app.db.seed_data import seed_initial_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and demo data is seeded
    logger.info("Initializing UniMind AI & AegisOps database schema and seed data...")
    try:
        seed_initial_data()
        logger.info("Database schema and seed data successfully verified.")
    except Exception as e:
        logger.error(f"Error during database startup seed: {e}")
    yield
    # Shutdown
    logger.info("Shutting down UniMind AI & AegisOps API engine.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="UniMind AI & AegisOps University Operations and Predictive AIOps Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    logger.info(f"[{request.method}] {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
    return response


# Include V1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)
# Root level health shortcut
app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API Engine",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }
