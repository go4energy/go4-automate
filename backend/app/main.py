"""go4-automate - FastAPI Application."""

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import settings
from app.exceptions import AppError
from app.routers import leads_router, llm_router, templates_router, tenants_router

# Loguru Konfiguration
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.debug else "INFO",
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="30 days",
    compression="gz",
    level="INFO",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting go4-automate API")
    yield
    logger.info("Shutting down go4-automate API")


app = FastAPI(
    title="go4-automate API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)


# Global Exception Handler
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle custom application errors."""
    logger.error(f"AppError: {exc.message} (status={exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


# Health Check
@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Health check endpoint for monitoring and Docker healthchecks."""
    return {"status": "healthy", "version": "0.1.0"}


# Router includes
app.include_router(leads_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(templates_router, prefix="/api/v1")
app.include_router(llm_router, prefix="/api/v1")
