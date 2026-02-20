"""go4-automate - FastAPI Application."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import settings
from app.exceptions import AppError

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
    # Auto-seed prompts for active tenant
    try:
        from app.database import async_session
        from app.services.prompt_seed import seed_prompts

        async with async_session() as db:
            created = await seed_prompts(db, settings.active_tenant)
            if created > 0:
                await db.commit()
                logger.info(
                    "Seeded {count} prompts for {tenant}",
                    count=created,
                    tenant=settings.active_tenant,
                )
    except Exception as e:
        logger.warning("Prompt seeding uebersprungen: {err}", err=str(e))
    yield
    logger.info("Shutting down go4-automate API")


app = FastAPI(
    title="go4-automate API",
    version="0.2.0",
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
    return {"status": "healthy", "version": "0.2.0"}


# Static files for uploads
upload_path = Path(settings.upload_dir)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

# Shared routers (remain in routers/)
from app.routers import (  # noqa: E402
    activity_router,
    chat_router,
    llm_router,
    prompts_router,
    templates_router,
    tenants_router,
)

app.include_router(tenants_router, prefix="/api/v1")
app.include_router(templates_router, prefix="/api/v1")
app.include_router(llm_router, prefix="/api/v1")
app.include_router(prompts_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(activity_router, prefix="/api/v1")

# Domain module routers
from app.collector.router import router as collector_router  # noqa: E402
from app.creator.router import router as creator_router  # noqa: E402
from app.crm.router import router as crm_router  # noqa: E402
from app.distributor.router import router as distributor_router  # noqa: E402
from app.setup.router import router as setup_router  # noqa: E402

app.include_router(collector_router, prefix="/api/v1")
app.include_router(creator_router, prefix="/api/v1")
app.include_router(distributor_router, prefix="/api/v1")
app.include_router(crm_router, prefix="/api/v1")
app.include_router(setup_router, prefix="/api/v1")
