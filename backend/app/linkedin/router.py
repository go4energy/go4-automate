"""LinkedIn API router."""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.linkedin.schemas import (
    LinkedInAccountCreate,
    LinkedInAccountListResponse,
    LinkedInAccountResponse,
    LinkedInAccountUpdate,
    LinkedInAutoLoginRequest,
    LinkedInAutoLoginResponse,
    LinkedInContactListResponse,
    LinkedInContactResponse,
    LinkedInImportRequest,
    LinkedInImportResult,
    LinkedInJobCreate,
    LinkedInJobListResponse,
    LinkedInJobLogListResponse,
    LinkedInJobLogResponse,
    LinkedInJobResponse,
    LinkedInJobStartResponse,
    LinkedInJobUpdate,
    LinkedInLoginRequest,
    LinkedInLoginResponse,
    LinkedInManualUrlImport,
    LinkedInManualUrlImportResult,
    LinkedInSessionImport,
    LinkedInSessionImportResponse,
    LinkedInSessionVerifyResponse,
    LinkedInSetPasswordRequest,
    LinkedInStats,
)
from app.linkedin.service import (
    AccountService,
    ContactService,
    JobLogService,
    JobService,
    LinkedInStatsService,
)
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/linkedin", tags=["linkedin"])


# ============== Stats ==============


@router.get("/stats", response_model=LinkedInStats)
async def get_linkedin_stats(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInStats:
    """Get LinkedIn module statistics."""
    try:
        service = LinkedInStatsService(db)
        stats = await service.get_stats(tenant_id)
        return LinkedInStats(**stats)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_linkedin_stats")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Safety Limits (Read-Only) ==============


@router.get("/safety-limits")
async def get_safety_limits() -> dict:
    """
    Get LinkedIn automation safety limits.
    These are system-wide settings that control human-like behavior.
    Read-only - can only be modified by admins via config file.
    """
    from app.linkedin.safety import get_all_limits

    return get_all_limits()


# ============== Account Endpoints ==============


@router.get("/accounts", response_model=list[LinkedInAccountListResponse])
async def list_accounts(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
) -> list[LinkedInAccountListResponse]:
    """List all LinkedIn accounts."""
    try:
        service = AccountService(db)
        accounts = await service.list_accounts(tenant_id, status=status_filter)

        return [
            LinkedInAccountListResponse(
                id=a.id,
                name=a.name,
                email=a.email,
                status=a.status,
                is_sales_navigator=a.is_sales_navigator,
                profiles_scraped_today=a.profiles_scraped_today,
                connections_sent_today=a.connections_sent_today,
                messages_sent_today=a.messages_sent_today,
                daily_profile_limit=a.daily_profile_limit,
                daily_connection_limit=a.daily_connection_limit,
                daily_message_limit=a.daily_message_limit,
                warmup_enabled=a.warmup_enabled,
                warmup_day=a.warmup_day,
                last_login_at=a.last_login_at,
                has_valid_session=_has_valid_session(a),
                job_count=len(a.scraper_jobs),
                created_at=a.created_at,
            )
            for a in accounts
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_accounts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/accounts",
    response_model=LinkedInAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_account(
    data: LinkedInAccountCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInAccountResponse:
    """Create a new LinkedIn account."""
    try:
        service = AccountService(db)
        account = await service.create(tenant_id, data)
        return _account_to_response(account)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_account")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/accounts/{account_id}", response_model=LinkedInAccountResponse)
async def get_account(
    account_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInAccountResponse:
    """Get a LinkedIn account by ID."""
    try:
        service = AccountService(db)
        account = await service.get_by_id(tenant_id, account_id)
        return _account_to_response(account)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_account")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/accounts/{account_id}", response_model=LinkedInAccountResponse)
async def update_account(
    account_id: int,
    data: LinkedInAccountUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInAccountResponse:
    """Update a LinkedIn account."""
    try:
        service = AccountService(db)
        account = await service.update(tenant_id, account_id, data)
        return _account_to_response(account)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_account")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a LinkedIn account."""
    try:
        service = AccountService(db)
        await service.delete(tenant_id, account_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_account")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/accounts/{account_id}/login", response_model=LinkedInLoginResponse)
async def initiate_login(
    account_id: int,
    data: LinkedInLoginRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInLoginResponse:
    """Initiate browser login for a LinkedIn account (Phase 2)."""
    try:
        # Phase 2: This will start Playwright browser for manual login
        service = AccountService(db)
        await service.get_by_id(tenant_id, account_id)

        return LinkedInLoginResponse(
            status="pending",
            message="Browser-Login wird in Phase 2 implementiert. "
            "Bitte Session manuell importieren.",
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in initiate_login")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/accounts/{account_id}/verify", response_model=LinkedInSessionVerifyResponse
)
async def verify_session(
    account_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInSessionVerifyResponse:
    """Verify if the account session is valid."""
    try:
        service = AccountService(db)
        account = await service.get_by_id(tenant_id, account_id)

        valid = _has_valid_session(account)
        return LinkedInSessionVerifyResponse(
            valid=valid,
            expires_at=account.session_expires_at,
            is_sales_navigator=account.is_sales_navigator,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in verify_session")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/accounts/{account_id}/import-session",
    response_model=LinkedInSessionImportResponse,
)
async def import_session(
    account_id: int,
    data: LinkedInSessionImport,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInSessionImportResponse:
    """Import browser session/cookies for a LinkedIn account.

    This allows importing session data exported from browser extensions
    like EditThisCookie or from Playwright's storageState.
    """
    import base64
    import struct
    from datetime import timedelta

    def extract_li_at_expiry(token_value: str) -> datetime | None:
        """Extract expiration timestamp from li_at token."""
        try:
            padded = token_value + "=" * (4 - len(token_value) % 4)
            decoded = base64.urlsafe_b64decode(padded)

            # Find timestamps by scanning for 0x000001 prefix (ms since epoch)
            for offset in [20, 22, 12, 14]:  # Check common offsets
                if len(decoded) >= offset + 8:
                    chunk = decoded[offset:offset + 8]
                    if chunk[0:3] == b'\x00\x00\x01':
                        ts_ms = struct.unpack(">Q", chunk)[0]
                        dt = datetime.fromtimestamp(ts_ms / 1000)
                        # Check if valid year and expiry is in future
                        if 2024 <= dt.year <= 2030 and dt > datetime.utcnow():
                            return dt
        except Exception:
            pass
        return None

    try:
        service = AccountService(db)
        account = await service.get_by_id(tenant_id, account_id)

        if not data.cookies and not data.storage_state:
            raise HTTPException(
                status_code=400,
                detail="Entweder cookies oder storage_state muss angegeben werden",
            )

        # Extract expiry from li_at token if possible
        expires_at = None
        if data.cookies:
            for cookie in data.cookies:
                if cookie.get("name") == "li_at" and cookie.get("value"):
                    expires_at = extract_li_at_expiry(cookie["value"])
                    break

        # Fallback to 30 days if extraction fails
        if not expires_at:
            expires_at = datetime.utcnow() + timedelta(days=30)

        if data.storage_state:
            # Full Playwright storage state
            session_data = {
                "storage_state": data.storage_state,
                "saved_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat(),
            }
        else:
            # Convert cookies to storage state format
            linkedin_cookies = [
                c for c in data.cookies if "linkedin.com" in c.get("domain", "")
            ]
            session_data = {
                "storage_state": {
                    "cookies": linkedin_cookies,
                    "origins": [],
                },
                "saved_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat(),
            }

        # Update account
        account.session_data = session_data
        account.session_expires_at = expires_at
        account.status = "active"
        account.last_error = None
        await db.commit()

        logger.info(
            "Session imported for account {id}: {email}",
            id=account_id,
            email=account.email,
        )

        return LinkedInSessionImportResponse(
            success=True,
            message="Session erfolgreich importiert",
            session_expires_at=expires_at,
        )

    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unerwarteter Fehler in import_session")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/accounts/{account_id}/set-password")
async def set_account_password(
    account_id: int,
    data: LinkedInSetPasswordRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Set/update password for a LinkedIn account (encrypted storage)."""
    from cryptography.fernet import Fernet

    from app.config import settings

    try:
        service = AccountService(db)
        account = await service.get_by_id(tenant_id, account_id)

        # Encrypt password
        key = settings.secret_key.encode()[:32].ljust(32, b"=")
        fernet = Fernet(__import__("base64").urlsafe_b64encode(key))
        encrypted = fernet.encrypt(data.password.encode()).decode()

        account.password_encrypted = encrypted
        await db.commit()

        return {"success": True, "message": "Passwort gespeichert"}

    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler beim Speichern des Passworts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/accounts/{account_id}/auto-login", response_model=LinkedInAutoLoginResponse)
async def auto_login(
    account_id: int,
    data: LinkedInAutoLoginRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInAutoLoginResponse:
    """Start automated login process for a LinkedIn account.

    Opens browser, enters credentials, and handles 2FA if needed.
    User can watch/interact via VNC at port 5901.
    """
    import base64
    import struct
    from datetime import timedelta

    def extract_li_at_expiry(cookies: list[dict]) -> datetime | None:
        """Extract expiration from li_at cookie."""
        for cookie in cookies:
            if cookie.get("name") == "li_at":
                try:
                    token = cookie.get("value", "")
                    padded = token + "=" * (4 - len(token) % 4)
                    decoded = base64.urlsafe_b64decode(padded)

                    # Find expiry timestamp by scanning for 0x000001 prefix
                    for offset in [20, 22, 12, 14]:
                        if len(decoded) >= offset + 8:
                            chunk = decoded[offset:offset + 8]
                            if chunk[0:3] == b'\x00\x00\x01':
                                ts_ms = struct.unpack(">Q", chunk)[0]
                                dt = datetime.fromtimestamp(ts_ms / 1000)
                                if 2024 <= dt.year <= 2030 and dt > datetime.utcnow():
                                    return dt
                except Exception:
                    pass
        return None

    try:
        service = AccountService(db)
        account = await service.get_by_id(tenant_id, account_id)

        # Get password - either from request or stored
        password = data.password
        if not password and account.password_encrypted:
            try:
                svc = AccountService(db)
                password = svc._decrypt_password(account.password_encrypted)
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail="Gespeichertes Passwort konnte nicht entschluesselt werden. "
                    "Bitte Passwort im Account neu speichern.",
                ) from exc

        if not password:
            raise HTTPException(
                status_code=400,
                detail="Kein Passwort gespeichert. Bitte zuerst das Passwort im Account hinterlegen.",
            )

        # Get browser from global manager (same browser as worker/debug)
        from app.linkedin.browser_manager import browser_manager

        browser = await browser_manager.get_browser(
            account_id=account.id,
            account_email=account.email,
            session_data=account.session_data,
            tenant_id=account.tenant_id,
        )

        result = await browser.login(
            email=account.email,
            password=password,
            wait_for_2fa_timeout=data.wait_for_2fa_timeout,
        )

        if not result.get("success"):
            account.last_error = result.get("error", "Login fehlgeschlagen")
            await db.commit()

            return LinkedInAutoLoginResponse(
                success=False,
                message=result.get("error", "Login fehlgeschlagen"),
                needs_manual_intervention=result.get("needs_manual_intervention", False),
            )

        # Save session via browser_manager
        session_data = await browser_manager.save_session(
            account.id, db=db, account=account
        )

        if session_data:
            # Try to extract real expiry from cookies
            cookies = session_data.get("storage_state", {}).get("cookies", [])
            expires_at = extract_li_at_expiry(cookies)
            if not expires_at:
                expires_at = datetime.utcnow() + timedelta(days=7)

            account.session_expires_at = expires_at
            account.status = "active"
            account.last_login_at = datetime.utcnow()
            account.last_error = None
            await db.commit()

            logger.info(
                "Auto-login successful for {email}, expires {expires}",
                email=account.email,
                expires=expires_at,
            )

            return LinkedInAutoLoginResponse(
                success=True,
                message="Login erfolgreich",
                session_expires_at=expires_at,
            )

        return LinkedInAutoLoginResponse(
            success=False,
            message="Login erfolgreich, aber Session konnte nicht gespeichert werden",
        )

    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unerwarteter Fehler in auto_login")
        raise HTTPException(status_code=500, detail=f"Interner Serverfehler: {e}") from e


# ============== Job Endpoints ==============


@router.get("/jobs", response_model=list[LinkedInJobListResponse])
async def list_jobs(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    account_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
) -> list[LinkedInJobListResponse]:
    """List all scraper jobs."""
    try:
        service = JobService(db)
        jobs = await service.list_jobs(
            tenant_id, account_id=account_id, status=status_filter
        )

        return [_job_to_list_response(j) for j in jobs]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_jobs")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/jobs",
    response_model=LinkedInJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job(
    data: LinkedInJobCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInJobResponse:
    """Create a new scraper job."""
    try:
        service = JobService(db)
        job = await service.create(tenant_id, data)
        # Reload with relations
        job = await service.get_by_id(tenant_id, job.id)
        return _job_to_response(job)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_job")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/jobs/{job_id}", response_model=LinkedInJobResponse)
async def get_job(
    job_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInJobResponse:
    """Get a scraper job by ID."""
    try:
        service = JobService(db)
        job = await service.get_by_id(tenant_id, job_id)
        return _job_to_response(job)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_job")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/jobs/{job_id}", response_model=LinkedInJobResponse)
async def update_job(
    job_id: int,
    data: LinkedInJobUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInJobResponse:
    """Update a scraper job."""
    try:
        service = JobService(db)
        job = await service.update(tenant_id, job_id, data)
        job = await service.get_by_id(tenant_id, job_id)
        return _job_to_response(job)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_job")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a scraper job."""
    try:
        service = JobService(db)
        await service.delete(tenant_id, job_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_job")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/jobs/{job_id}/start", response_model=LinkedInJobStartResponse)
async def start_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInJobStartResponse:
    """Start a scraper job.

    Sets job to queued, then runs it as a background task.
    If debug mode is active (WebSocket connected), the worker will
    pause at each step for approval. Otherwise it runs automatically.
    """
    try:
        service = JobService(db)
        await service.start_job(tenant_id, job_id)

        # Run job in background (non-blocking)
        from app.database import async_session
        from app.linkedin.scraper.worker import process_job_now

        background_tasks.add_task(process_job_now, async_session, job_id)

        return LinkedInJobStartResponse(
            status="running",
            message="Job gestartet",
            job_id=job_id,
        )

    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in start_job")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/jobs/{job_id}/pause", response_model=LinkedInJobResponse)
async def pause_job(
    job_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInJobResponse:
    """Pause a running job."""
    try:
        service = JobService(db)
        job = await service.pause_job(tenant_id, job_id)
        job = await service.get_by_id(tenant_id, job_id)
        return _job_to_response(job)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in pause_job")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/jobs/{job_id}/cancel", response_model=LinkedInJobResponse)
async def cancel_job(
    job_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInJobResponse:
    """Cancel a job."""
    try:
        service = JobService(db)
        job = await service.cancel_job(tenant_id, job_id)
        job = await service.get_by_id(tenant_id, job_id)
        return _job_to_response(job)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in cancel_job")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/jobs/{job_id}/urls", response_model=LinkedInManualUrlImportResult)
async def add_manual_urls(
    job_id: int,
    data: LinkedInManualUrlImport,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInManualUrlImportResult:
    """Add profile URLs manually to a job."""
    try:
        service = JobService(db)
        return await service.add_manual_urls(tenant_id, job_id, data)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in add_manual_urls")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Job Log Endpoints ==============


@router.get("/jobs/{job_id}/logs", response_model=list[LinkedInJobLogListResponse])
async def list_job_logs(
    job_id: int,
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[LinkedInJobLogListResponse]:
    """List job execution logs."""
    try:
        # First verify job belongs to tenant
        job_service = JobService(db)
        await job_service.get_by_id(tenant_id, job_id)

        service = JobLogService(db)
        logs = await service.list_for_job(job_id, limit=limit)
        return [
            LinkedInJobLogListResponse(
                id=log.id,
                started_at=log.started_at,
                completed_at=log.completed_at,
                duration_seconds=log.duration_seconds,
                start_page=log.start_page,
                end_page=log.end_page,
                profiles_scraped=log.profiles_scraped,
                profiles_failed=log.profiles_failed,
                profiles_skipped=log.profiles_skipped,
                status=log.status,
                error_message=log.error_message,
            )
            for log in logs
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_job_logs")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/jobs/{job_id}/logs/{log_id}", response_model=LinkedInJobLogResponse)
async def get_job_log(
    job_id: int,
    log_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInJobLogResponse:
    """Get a specific job log entry."""
    try:
        # Verify job belongs to tenant
        job_service = JobService(db)
        await job_service.get_by_id(tenant_id, job_id)

        service = JobLogService(db)
        log = await service.get_by_id(job_id, log_id)
        return LinkedInJobLogResponse(
            id=log.id,
            job_id=log.job_id,
            started_at=log.started_at,
            completed_at=log.completed_at,
            duration_seconds=log.duration_seconds,
            start_page=log.start_page,
            end_page=log.end_page,
            profiles_scraped=log.profiles_scraped,
            profiles_failed=log.profiles_failed,
            profiles_skipped=log.profiles_skipped,
            status=log.status,
            error_message=log.error_message,
            created_at=log.created_at,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_job_log")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Contact Endpoints ==============


@router.get("/jobs/{job_id}/contacts", response_model=list[LinkedInContactListResponse])
async def list_job_contacts(
    job_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[LinkedInContactListResponse]:
    """List all contacts for a job."""
    try:
        service = ContactService(db)
        contacts = await service.list_for_job(tenant_id, job_id)
        return [_contact_to_list_response(c) for c in contacts]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_job_contacts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/jobs/{job_id}/import", response_model=LinkedInImportResult)
async def import_contacts(
    job_id: int,
    data: LinkedInImportRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInImportResult:
    """Import job contacts to a funnel."""
    try:
        service = ContactService(db)
        return await service.import_to_funnel(tenant_id, job_id, data)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in import_contacts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/contacts", response_model=list[LinkedInContactListResponse])
async def list_all_contacts(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    imported: bool | None = Query(None),
) -> list[LinkedInContactListResponse]:
    """List all LinkedIn contacts."""
    try:
        service = ContactService(db)
        contacts = await service.list_contacts(
            tenant_id, status=status_filter, imported=imported
        )
        # Load pipeline counts for contacts with central_contact_id
        central_ids = [
            c.central_contact_id for c in contacts if c.central_contact_id
        ]
        pipeline_counts: dict[int, int] = {}
        if central_ids:
            from sqlalchemy import func as sa_func
            from sqlalchemy import select as sa_select

            from app.engagement.models import PipelineEnrollment

            count_result = await db.execute(
                sa_select(
                    PipelineEnrollment.contact_id,
                    sa_func.count(PipelineEnrollment.id),
                )
                .where(PipelineEnrollment.contact_id.in_(central_ids))
                .group_by(PipelineEnrollment.contact_id)
            )
            pipeline_counts = dict(count_result.all())

        return [
            _contact_to_list_response(
                c, pipeline_counts.get(c.central_contact_id or 0, 0)
            )
            for c in contacts
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_all_contacts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/contacts/{contact_id}", response_model=LinkedInContactResponse)
async def get_contact(
    contact_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInContactResponse:
    """Get a LinkedIn contact by ID."""
    try:
        service = ContactService(db)
        contact = await service.get_by_id(tenant_id, contact_id)
        resp = LinkedInContactResponse.model_validate(contact)

        # Load pipeline enrollments
        if contact.central_contact_id:
            from sqlalchemy import select as sa_select

            from app.engagement.models import (
                EngagementPipeline,
                PipelineEnrollment,
            )

            enroll_result = await db.execute(
                sa_select(PipelineEnrollment, EngagementPipeline.name)
                .join(
                    EngagementPipeline,
                    PipelineEnrollment.pipeline_id == EngagementPipeline.id,
                )
                .where(
                    PipelineEnrollment.contact_id == contact.central_contact_id
                )
            )
            enrollments = enroll_result.all()
            resp.pipeline_count = len(enrollments)
            resp.pipelines = [
                {
                    "id": e.PipelineEnrollment.pipeline_id,
                    "name": e.name,
                    "stage": e.PipelineEnrollment.stage,
                    "status": e.PipelineEnrollment.status,
                }
                for e in enrollments
            ]

        return resp
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_contact")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/contacts/{contact_id}/exclude")
async def toggle_exclude_contact(
    contact_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Toggle excluded status of a LinkedIn contact."""
    try:
        service = ContactService(db)
        contact = await service.get_by_id(tenant_id, contact_id)
        contact.excluded = not contact.excluded
        await db.commit()
        return {"id": contact.id, "excluded": contact.excluded}
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in toggle_exclude_contact")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Contact Delete ==============


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a single LinkedIn contact."""
    try:
        service = ContactService(db)
        await service.delete_contact(tenant_id, contact_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_contact")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/contacts/bulk-delete")
async def bulk_delete_contacts(
    data: dict,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete multiple LinkedIn contacts by IDs."""
    try:
        contact_ids = data.get("contact_ids", [])
        if not contact_ids:
            raise HTTPException(status_code=400, detail="Keine Kontakt-IDs angegeben")
        service = ContactService(db)
        deleted = await service.delete_contacts_bulk(tenant_id, contact_ids)
        return {"deleted": deleted}
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unerwarteter Fehler in bulk_delete_contacts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete(
    "/jobs/{job_id}/contacts", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_job_contacts(
    job_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete all contacts for a specific job."""
    try:
        service = ContactService(db)
        await service.delete_contacts_by_job(tenant_id, job_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_job_contacts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Contact Bridge ==============


@router.post("/contacts/{contact_id}/import-to-contacts")
async def import_to_central_contact(
    contact_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Import a LinkedIn contact as a central contact."""
    try:
        from app.linkedin.bridge_service import LinkedInBridgeService

        service = LinkedInBridgeService(db)
        contact = await service.import_as_contact(tenant_id, contact_id)
        await db.commit()
        return {
            "contact_id": contact.id,
            "name": contact.name,
            "email": contact.email,
        }
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Error importing LinkedIn contact to central")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/contacts/bulk-import-to-contacts")
async def bulk_import_to_central_contacts(
    data: dict,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import LinkedIn contacts as central contacts."""
    try:
        from app.linkedin.bridge_service import LinkedInBridgeService

        linkedin_contact_ids = data.get("linkedin_contact_ids", [])
        if not linkedin_contact_ids:
            raise HTTPException(status_code=400, detail="linkedin_contact_ids required")

        service = LinkedInBridgeService(db)
        result = await service.bulk_import_as_contacts(tenant_id, linkedin_contact_ids)
        await db.commit()
        return result
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Error bulk importing LinkedIn contacts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/contacts/{contact_id}/link-contact")
async def link_to_central_contact(
    contact_id: int,
    data: dict,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Link a LinkedIn contact to an existing central contact."""
    try:
        from app.linkedin.bridge_service import LinkedInBridgeService

        central_contact_id = data.get("contact_id")
        if not central_contact_id:
            raise HTTPException(status_code=400, detail="contact_id required")

        service = LinkedInBridgeService(db)
        await service.link_to_contact(tenant_id, contact_id, central_contact_id)
        await db.commit()
        return {"linked": True, "contact_id": central_contact_id}
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Error linking LinkedIn contact")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/contacts/{contact_id}/import-conversations")
async def import_conversations(
    contact_id: int,
    data: dict,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Import LinkedIn conversations as central contact activities."""
    try:
        from app.linkedin.bridge_service import LinkedInBridgeService

        central_contact_id = data.get("contact_id")
        if not central_contact_id:
            raise HTTPException(status_code=400, detail="contact_id required")

        service = LinkedInBridgeService(db)
        count = await service.import_conversations(
            tenant_id, contact_id, central_contact_id
        )
        await db.commit()
        return {"imported_messages": count, "contact_id": central_contact_id}
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Error importing conversations")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Helper Functions ==============


def _has_valid_session(account) -> bool:
    """Check if account has valid session."""
    if not account.session_data:
        return False
    if account.session_expires_at and account.session_expires_at < datetime.utcnow():
        return False
    return account.status == "active"


def _account_to_response(
    account, job_count: int | None = None
) -> LinkedInAccountResponse:
    """Convert account model to response.

    Args:
        account: The LinkedInAccount model
        job_count: Optional pre-computed job count. If None, tries to compute from
                   loaded relationship, or defaults to 0 if not loaded.
    """
    if job_count is None:
        # Check if relationship is loaded to avoid lazy loading errors
        from sqlalchemy.orm.attributes import instance_state

        state = instance_state(account)
        job_count = len(account.scraper_jobs) if "scraper_jobs" in state.dict else 0

    return LinkedInAccountResponse(
        id=account.id,
        tenant_id=account.tenant_id,
        name=account.name,
        email=account.email,
        status=account.status,
        is_sales_navigator=account.is_sales_navigator,
        daily_profile_limit=account.daily_profile_limit,
        daily_connection_limit=account.daily_connection_limit,
        daily_message_limit=account.daily_message_limit,
        profiles_scraped_today=account.profiles_scraped_today,
        connections_sent_today=account.connections_sent_today,
        messages_sent_today=account.messages_sent_today,
        total_profiles_scraped=account.total_profiles_scraped,
        warmup_enabled=account.warmup_enabled,
        warmup_day=account.warmup_day,
        last_login_at=account.last_login_at,
        last_scrape_date=account.last_scrape_date,
        last_error=account.last_error,
        session_expires_at=account.session_expires_at,
        has_valid_session=_has_valid_session(account),
        job_count=job_count,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def _job_to_response(job) -> LinkedInJobResponse:
    """Convert job model to response."""
    progress = 0.0
    if job.max_profiles > 0:
        progress = min(100.0, (job.profiles_scraped / job.max_profiles) * 100)

    return LinkedInJobResponse(
        id=job.id,
        tenant_id=job.tenant_id,
        account_id=job.account_id,
        funnel_id=job.funnel_id,
        pipeline_id=job.pipeline_id,
        name=job.name,
        job_type=job.job_type,
        search_url=job.search_url,
        profile_urls=job.profile_urls,
        max_profiles=job.max_profiles,
        daily_limit=job.daily_limit,
        min_delay_seconds=job.min_delay_seconds,
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        profiles_found=job.profiles_found,
        profiles_scraped=job.profiles_scraped,
        profiles_failed=job.profiles_failed,
        current_page=job.current_page,
        error_message=job.error_message,
        retry_count=job.retry_count,
        auto_import=job.auto_import,
        import_stage_id=job.import_stage_id,
        auto_enroll_pipeline=job.auto_enroll_pipeline,
        scrape_full_profiles=job.scrape_full_profiles,
        # Schedule settings
        schedule_enabled=job.schedule_enabled,
        schedule_days=job.schedule_days,
        schedule_start_time=job.schedule_start_time,
        schedule_end_time=job.schedule_end_time,
        max_pages_per_run=job.max_pages_per_run,
        # Computed
        account_name=job.account.name if job.account else None,
        funnel_name=job.funnel.name if job.funnel else None,
        pipeline_name=job.pipeline.name if job.pipeline else None,
        import_stage_name=job.import_stage.name if job.import_stage else None,
        progress_percent=progress,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _job_to_list_response(job) -> LinkedInJobListResponse:
    """Convert job model to list response."""
    progress = 0.0
    if job.max_profiles > 0:
        progress = min(100.0, (job.profiles_scraped / job.max_profiles) * 100)

    return LinkedInJobListResponse(
        id=job.id,
        account_id=job.account_id,
        funnel_id=job.funnel_id,
        pipeline_id=job.pipeline_id,
        name=job.name,
        job_type=job.job_type,
        status=job.status,
        profiles_found=job.profiles_found,
        profiles_scraped=job.profiles_scraped,
        profiles_failed=job.profiles_failed,
        max_profiles=job.max_profiles,
        current_page=job.current_page,
        schedule_enabled=job.schedule_enabled,
        max_pages_per_run=job.max_pages_per_run,
        auto_enroll_pipeline=job.auto_enroll_pipeline,
        progress_percent=progress,
        account_name=job.account.name if job.account else None,
        funnel_name=job.funnel.name if job.funnel else None,
        pipeline_name=job.pipeline.name if job.pipeline else None,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


def _contact_to_list_response(
    contact, pipeline_count: int = 0
) -> LinkedInContactListResponse:
    """Convert contact model to list response."""
    return LinkedInContactListResponse(
        id=contact.id,
        scraper_job_id=contact.scraper_job_id,
        linkedin_url=contact.linkedin_url,
        name=contact.name,
        headline=contact.headline,
        position=contact.position,
        company_name=contact.company_name,
        location=contact.location,
        contact_degree=contact.contact_degree,
        is_premium=contact.is_premium,
        gender=contact.gender,
        status=contact.status,
        excluded=contact.excluded,
        central_contact_id=contact.central_contact_id,
        pipeline_count=pipeline_count,
        imported_at=contact.imported_at,
        created_at=contact.created_at,
    )


# ============== Engagement Actions Queue ==============


@router.get("/engagement/actions")
async def get_engagement_actions(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    Get pending engagement actions for LinkedIn.

    These are actions created by the Engagement Brain that need to be
    processed by the LinkedIn module.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.engagement.models import PendingAction

    try:
        query = (
            select(PendingAction)
            .options(
                selectinload(PendingAction.contact),
                selectinload(PendingAction.pipeline),
            )
            .where(
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "linkedin",
            )
        )

        if status_filter:
            query = query.where(PendingAction.status == status_filter)
        else:
            # Default: Show actions that need attention
            query = query.where(
                PendingAction.status.in_(["pending", "ready_for_approval", "approved"])
            )

        query = query.order_by(
            PendingAction.priority.desc(),
            PendingAction.due_at.asc().nullslast(),
            PendingAction.created_at.asc(),
        ).limit(limit)

        result = await db.execute(query)
        actions = result.scalars().all()

        return [
            {
                "id": a.id,
                "contact_id": a.contact_id,
                "contact_name": a.contact.name if a.contact else None,
                "contact_email": a.contact.email if a.contact else None,
                "pipeline_id": a.pipeline_id,
                "pipeline_name": a.pipeline.name if a.pipeline else None,
                "action_type": a.action_type,
                "context": a.context,
                "suggested_content": a.suggested_content,
                "priority": a.priority,
                "due_at": a.due_at,
                "needs_approval": a.needs_approval,
                "status": a.status,
                "created_at": a.created_at,
            }
            for a in actions
        ]
    except Exception as e:
        logger.exception("Error getting engagement actions")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/engagement/actions/{action_id}/generate-content")
async def generate_action_content(
    action_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Generate content for a pending action using the LinkedIn module brain.

    This uses the pipeline's stored prompts and contact context to generate
    personalized LinkedIn content.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.engagement.models import PendingAction
    from app.services.llm import LLMService

    try:
        # Get the action
        result = await db.execute(
            select(PendingAction)
            .options(
                selectinload(PendingAction.contact),
                selectinload(PendingAction.pipeline),
            )
            .where(
                PendingAction.id == action_id,
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "linkedin",
            )
        )
        action = result.scalar_one_or_none()

        if not action:
            raise HTTPException(status_code=404, detail="Aktion nicht gefunden")

        context = action.context or {}
        pipeline = action.pipeline
        contact = action.contact

        # Build content generation prompt
        action_prompts = {
            "connection_request": "Schreibe eine kurze LinkedIn-Verbindungsanfrage (max 300 Zeichen)",
            "send_message": "Schreibe eine LinkedIn-Nachricht (max 500 Zeichen)",
            "send_inmail": "Schreibe eine LinkedIn InMail Nachricht",
        }

        action_desc = action_prompts.get(
            action.action_type, f"Schreibe eine Nachricht für: {action.action_type}"
        )

        prompt = f"""
{action_desc}

EMPFÄNGER:
- Name: {context.get('contact_name', contact.name if contact else 'Unbekannt')}
- Position: {context.get('contact_position', '')}
- Unternehmen: {context.get('contact_company', '')}

KONTEXT:
- Produkt: {context.get('product_name', pipeline.product_name if pipeline else '')}
- Ziel: {context.get('goal', pipeline.goal if pipeline else '')}
- Tonalität: {context.get('tone_of_voice', pipeline.tone_of_voice if pipeline else 'professionell')}
- Bisherige Kontakte: {context.get('touch_count', 0)}

Schreibe eine persönliche, authentische Nachricht ohne Spam-Charakter.
Antworte NUR mit dem Nachrichtentext, keine Erklärungen.
"""

        llm = LLMService()
        content = await llm.generate(task="content", prompt=prompt)

        # Update the action with the generated content
        action.suggested_content = content
        await db.commit()

        return {
            "action_id": action_id,
            "generated_content": content,
            "action_type": action.action_type,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating action content")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/engagement/actions/{action_id}/execute")
async def execute_engagement_action(
    action_id: int,
    content_override: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Execute an engagement action via LinkedIn.

    This will:
    1. Send the connection request/message via LinkedIn
    2. Log the activity
    3. Mark the action as completed
    """
    from datetime import datetime

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.engagement.models import PendingAction
    from app.linkedin.outreach_service import LinkedInOutreachService

    try:
        # Get the action
        result = await db.execute(
            select(PendingAction)
            .options(
                selectinload(PendingAction.contact),
                selectinload(PendingAction.pipeline),
                selectinload(PendingAction.enrollment),
            )
            .where(
                PendingAction.id == action_id,
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "linkedin",
                PendingAction.status.in_(["approved", "pending"]),
            )
        )
        action = result.scalar_one_or_none()

        if not action:
            raise HTTPException(
                status_code=404,
                detail="Aktion nicht gefunden oder nicht ausführbar",
            )

        # Get content to send
        content = content_override or action.suggested_content
        if not content and action.action_type in ["connection_request", "send_message"]:
            raise HTTPException(
                status_code=400,
                detail="Kein Inhalt für die Aktion vorhanden",
            )

        # Get contact's LinkedIn URL from context or contact
        linkedin_url = action.context.get("linkedin_url")
        if not linkedin_url and action.contact:
            # Try to get from contacts module
            from app.contacts.models import Contact

            contact_result = await db.execute(
                select(Contact).where(
                    Contact.id == action.contact_id,
                    Contact.tenant_id == tenant_id,
                )
            )
            contact = contact_result.scalar_one_or_none()
            if contact:
                linkedin_url = contact.linkedin

        if not linkedin_url:
            raise HTTPException(
                status_code=400,
                detail="Keine LinkedIn-URL für den Kontakt vorhanden",
            )

        # Execute the action
        outreach_service = LinkedInOutreachService(db)

        if action.action_type == "connection_request":
            # Send connection request
            from app.linkedin.schemas import SendConnectionRequest

            result_data = await outreach_service.send_connection_request(
                tenant_id=tenant_id,
                request=SendConnectionRequest(
                    profile_url=linkedin_url,
                    note=content[:300] if content else None,  # LinkedIn limit
                ),
            )
        elif action.action_type == "send_message":
            # Send message
            from app.linkedin.schemas import SendMessageRequest

            result_data = await outreach_service.send_message(
                tenant_id=tenant_id,
                request=SendMessageRequest(
                    profile_url=linkedin_url,
                    message=content,
                ),
            )
        else:
            # Unknown action type - just mark as completed
            result_data = {"status": "skipped", "reason": f"Unknown action type: {action.action_type}"}

        # Mark action as completed
        action.status = "completed"
        action.completed_at = datetime.utcnow()
        action.result = result_data

        # Update enrollment touch tracking
        if action.enrollment:
            action.enrollment.touch_count += 1
            action.enrollment.last_touch_at = datetime.utcnow()

        await db.commit()

        return {
            "action_id": action_id,
            "status": "completed",
            "result": result_data,
        }
    except HTTPException:
        raise
    except AppError as e:
        # Mark action as failed
        action.status = "failed"
        action.error_message = e.message
        await db.commit()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Error executing engagement action")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Scheduler Endpoints ==============


@router.get("/scheduler/status")
async def get_scheduler_status(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get scheduler status for all scheduled jobs."""
    from app.database import async_session
    from app.linkedin.scheduler import LinkedInScheduler

    scheduler = LinkedInScheduler(async_session)
    return await scheduler.get_status()
