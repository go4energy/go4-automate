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

    from app.database import async_session

    # Auto-seed admin user for active tenant
    try:
        from app.auth.service import AuthService

        async with async_session() as db:
            service = AuthService(db)
            admin = await service.ensure_admin_exists(
                settings.active_tenant, settings.initial_admin_password
            )
            if admin:
                await db.commit()
    except Exception as e:
        logger.warning("Admin seeding uebersprungen: {err}", err=str(e))

    # Auto-seed prompts for active tenant
    try:
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

    # Auto-seed AI prompts from module manifests
    try:
        from app.ai.seeder import seed_module_prompts
        from app.utils.module_discovery import discover_manifests

        module_manifests = discover_manifests(Path(__file__).parent)
        async with async_session() as db:
            created = await seed_module_prompts(
                db, settings.active_tenant, list(module_manifests.values())
            )
            if created > 0:
                logger.info(
                    "Seeded {count} AI prompts for {tenant}",
                    count=created,
                    tenant=settings.active_tenant,
                )
    except Exception as e:
        logger.warning("AI prompt seeding uebersprungen: {err}", err=str(e))

    yield
    logger.info("Shutting down go4-automate API")


app = FastAPI(
    title="go4-automate API",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS - extend with common development IPs
cors_origins = list(settings.allowed_origins)
for ip in ["192.168.1.227", "127.0.0.1", "localhost"]:
    for port in [8081, 5173, 3000]:
        origin = f"http://{ip}:{port}"
        if origin not in cors_origins:
            cors_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Auth paths exempt from JWT check
AUTH_EXEMPT_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})
AUTH_EXEMPT_PREFIXES = (
    "/api/v1/listen/",
    "/api/v1/surveys/public/",
    "/api/v1/emailmarketing/t/",  # Email tracking (open, click, unsubscribe)
    "/api/v1/emailmarketing/webhooks/",  # Email provider webhooks
    "/api/v1/whatsapp/webhook",  # Meta WhatsApp webhook (verification + events)
    "/api/v1/briefing/oauth/callback",  # Provider callback resolves tenant via state
    "/api/v1/briefing/personal/oauth/callback",  # Provider callback resolves tenant via state
    "/api/v1/assistant/oauth/callback",  # Assistant OAuth resolves tenant via state
    "/uploads/",
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Enforce tenant header + JWT auth on all /api/v1/ routes."""
    path = request.url.path

    # Skip OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return await call_next(request)

    # Skip non-API paths and exempt routes
    needs_auth = path.startswith("/api/v1/")
    if not needs_auth or path in AUTH_EXEMPT_PATHS:
        return await call_next(request)
    for prefix in AUTH_EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return await call_next(request)

    # Allow backend-secret for n8n/internal calls
    backend_secret = request.headers.get("X-Backend-Secret", "")
    if (
        backend_secret
        and settings.backend_secret
        and backend_secret == settings.backend_secret
    ):
        return await call_next(request)

    # Require explicit tenant context for protected tenant-scoped routes
    needs_tenant_header = not (
        path == "/api/v1/tenants" or path.startswith("/api/v1/tenants/")
    )
    if needs_tenant_header and not request.headers.get("X-Tenant-ID"):
        return JSONResponse(
            status_code=400,
            content={"detail": "X-Tenant-ID Header fehlt"},
        )

    # Login needs tenant context, but no Bearer token yet
    if path == "/api/v1/auth/login":
        return await call_next(request)

    # Check for Bearer token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "Nicht authentifiziert"},
        )

    return await call_next(request)


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

# Auto-discover domain modules
from app.utils.module_discovery import (  # noqa: E402
    discover_manifests,
    register_interfaces,
    register_models,
    register_routers,
)

manifests = discover_manifests(Path(__file__).parent)
register_models(manifests)
register_interfaces(manifests)

# Shared routers (remain in routers/)
from app.ai.router import router as ai_router  # noqa: E402
from app.routers import (  # noqa: E402
    activity_router,
    chat_router,
    llm_router,
    modules_router,
    prompts_router,
    streams_router,
    tags_router,
    templates_router,
    tenants_router,
)

app.include_router(tenants_router, prefix="/api/v1")
app.include_router(templates_router, prefix="/api/v1")
app.include_router(llm_router, prefix="/api/v1")
app.include_router(prompts_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(activity_router, prefix="/api/v1")
app.include_router(modules_router, prefix="/api/v1")
app.include_router(tags_router, prefix="/api/v1")
app.include_router(streams_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")

# Domain module routers (auto-discovered from __manifest__.py)
register_routers(app, manifests, prefix="/api/v1")

# WebSocket routes (no prefix, no auth middleware)
from app.assistant.realtime_voice import router as realtime_voice_router  # noqa: E402

app.include_router(realtime_voice_router)
