"""LinkedIn Debug WebSocket router.

Provides a WebSocket endpoint for global worker debug control.
When connected, polls for queued jobs and runs them through the normal worker.

Also provides a REST endpoint for single-profile scraping/testing.
"""

import asyncio
import contextlib
import json
import traceback

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.linkedin.browser_manager import browser_manager
from app.linkedin.debug_bridge import bridge
from app.linkedin.models import LinkedInAccount, LinkedInScraperJob
from app.linkedin.scraper.profile_extractor import extract_profile_from_sections
from app.linkedin.scraper.worker import LinkedInWorker
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/linkedin/debug", tags=["linkedin-debug"])


class ScrapeProfileRequest(BaseModel):
    """Request body for single-profile scraping."""

    url: str
    account_id: int | None = None


@router.post("/scrape-profile")
async def scrape_single_profile(
    req: ScrapeProfileRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Full profile scrape — identical sequence to worker.

    1. Open browser with session
    2. Navigate to profile, wait for Topcard
    3. Scroll full page (lazy-load all sections)
    4. Extract ALL sections via JS componentkeys
    5. Parse sections → structured profile
    6. Open contact info modal → extract email/phone/website/etc.
    7. Navigate to interests page → extract companies/groups/etc.
    8. Return everything
    """
    # Find account
    account = await _get_account(req, tenant_id, db)

    steps: list[dict] = []

    def step(name: str, status: str, detail: str = "") -> None:
        steps.append({"step": name, "status": status, "detail": detail})
        logger.info(
            "Debug scrape [{status}] {name}: {detail}",
            status=status,
            name=name,
            detail=detail,
        )

    try:
        # --- 1. Get browser from global manager ---
        already_open = browser_manager.has_browser(account.id)
        browser = await browser_manager.get_browser(
            account_id=account.id,
            account_email=account.email,
            session_data=account.session_data,
            tenant_id=account.tenant_id,
        )
        if already_open:
            step("browser", "ok", f"Wiederverwendet: {account.email}")
        else:
            step("browser", "start", f"Neuer Browser: {account.email}")

        # --- 2. Check session ---
        session_ok = await browser.check_session_valid()
        if not session_ok:
            step("session", "fail", "Session ungültig — bitte im offenen Browser einloggen und erneut scrapen")
            return {
                "success": False,
                "error": "LinkedIn-Session ungültig. Bitte im offenen Browser einloggen und dann erneut starten.",
                "steps": steps,
            }
        step("session", "ok", "Eingeloggt")

        # Save session to DB after successful validation
        await browser_manager.save_session(
            account.id, db=db, account=account
        )

        # Reactivate account if it was expired
        if account.status != "active":
            old_status = account.status
            account.status = "active"
            account.last_error = None
            await db.commit()
            step("account", "ok", f"Account reaktiviert (war: {old_status})")

        # --- 3. Navigate to profile, wait 0.5s ---
        nav_ok = await browser._goto(req.url, browser.SEL_TOPCARD, timeout=20000)
        if not nav_ok:
            step("navigate", "fail", req.url)
            return {
                "success": False,
                "error": f"Profil konnte nicht geladen werden: {req.url}",
                "steps": steps,
            }
        await asyncio.sleep(0.5)
        step("navigate", "ok", req.url)

        # --- 4. Scroll: PageDown 1s hold, wait 0.5s, PageUp 1s hold ---
        await browser.scroll_profile_naturally()
        step("scroll", "ok", "Profil gescrollt (down 1s + up 1s)")

        # --- 5. Extract sections + save HTML ---
        sections = await browser.extract_profile_sections()
        found = [k for k, v in sections.items() if v and not k.startswith("_")]
        step("sections", "ok", f"{len(found)} gefunden: {', '.join(found)}")

        # Save profile HTML (debug only)
        from pathlib import Path

        data_dir = Path("data/profiles")
        data_dir.mkdir(parents=True, exist_ok=True)
        slug = req.url.rstrip("/").split("/in/")[-1].split("/")[0].split("?")[0]
        try:
            html_path = data_dir / f"{slug}.html"
            full_html = await browser.get_page_content()
            html_path.write_text(full_html, encoding="utf-8")
            step("save_html", "ok", f"{html_path} ({len(full_html)} bytes)")
        except Exception as e:
            step("save_html", "warn", str(e))

        # --- 6. Parse sections → structured profile ---
        profile = extract_profile_from_sections(sections)
        step(
            "parse",
            "ok",
            f"name={profile.get('name')}, exp={len(profile.get('experience', []))}, "
            f"edu={len(profile.get('education', []))}, skills={len(profile.get('skills', []))}",
        )

        # --- 7. Contact info: open, read, wait 0.5s, close ---
        try:
            modal_html = await browser.click_contact_info()
            if modal_html:
                contact_info = await browser.extract_contact_info_from_modal()
                await asyncio.sleep(0.5)
                if contact_info:
                    profile["contact_info"] = contact_info
                    step(
                        "contact_info",
                        "ok",
                        f"Felder: {', '.join(contact_info.keys())}",
                    )
                else:
                    step("contact_info", "warn", "Modal geöffnet, aber keine Daten")
            else:
                step("contact_info", "warn", "Kein Kontaktinfo-Button gefunden")
        except Exception as e:
            step("contact_info", "fail", str(e))

        # --- 8. Interests: navigate, per tab scroll + scrape + save HTML ---
        try:
            interests_ok = await browser.navigate_to_interests_page(
                slug, save_dir=str(data_dir)
            )
            if interests_ok:
                interests = await browser.extract_interests_page()
                if interests and any(interests.values()):
                    profile["interests"] = interests
                    total = sum(
                        len(v) for v in interests.values() if isinstance(v, list)
                    )
                    step("interests", "ok", f"{total} Interessen gefunden")
                else:
                    step("interests", "warn", "Interessen-Seite geladen, aber leer")
            else:
                step("interests", "warn", "Interessen-Seite nicht erreichbar")
        except Exception as e:
            step("interests", "fail", str(e))

        # --- 9. Connection status ---
        try:
            await browser._goto(req.url, browser.SEL_TOPCARD, timeout=15000)
            conn_status = await browser._get_connection_status()
            if conn_status:
                profile["connection_status"] = conn_status
                step("connection_status", "ok", conn_status)
        except Exception as e:
            step("connection_status", "fail", str(e))

        # --- Build response ---
        found_sections = [k for k, v in sections.items() if v and not k.startswith("_")]

        return {
            "success": True,
            "url": req.url,
            "account": account.name,
            "found_sections": found_sections,
            "raw_sections": {
                k: v[:3000] if isinstance(v, str) else v
                for k, v in sections.items()
                if v and not k.startswith("_")
            },
            "profile": profile,
            "steps": steps,
        }

    except Exception as e:
        logger.exception("Debug scrape error")
        step("fatal", "fail", str(e))
        # Browser bleibt offen (managed by browser_manager)
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "steps": steps,
        }


async def _get_account(
    req: ScrapeProfileRequest,
    tenant_id: str,
    db: AsyncSession,
) -> LinkedInAccount:
    """Resolve the LinkedIn account to use."""
    if req.account_id:
        account = await db.get(LinkedInAccount, req.account_id)
        if not account or account.tenant_id != tenant_id:
            raise HTTPException(404, "Account nicht gefunden")
        return account

    result = await db.execute(
        select(LinkedInAccount)
        .where(
            LinkedInAccount.tenant_id == tenant_id,
            LinkedInAccount.status.in_(["active", "inactive"]),
        )
        .order_by(LinkedInAccount.last_login_at.desc().nullslast())
        .limit(1)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(400, "Kein LinkedIn-Account vorhanden")
    return account


@router.websocket("/ws")
async def debug_websocket(websocket: WebSocket):
    """WebSocket for global worker debug control.

    Connect with: ws://host:8000/api/v1/linkedin/debug/ws

    Client sends:
        {"action": "continue"}  — Approve current step
        {"action": "cancel"}    — Cancel current job

    Server sends:
        {"type": "step", ...}     — Step waiting for approval
        {"type": "log", ...}      — Log message
        {"type": "finished", ...} — Job completed/cancelled/error
        {"type": "status", ...}   — Debug mode status
    """
    await websocket.accept()
    logger.info("Debug WebSocket connected")

    # Activate debug bridge
    bridge.connect(websocket)

    await websocket.send_json(
        {
            "type": "status",
            "active": True,
            "message": "Debug-Modus aktiviert. Starte einen Job im Jobs-Tab.",
        }
    )

    # Background task: poll for queued jobs
    poll_task = asyncio.create_task(_poll_and_run_jobs(websocket))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            action = msg.get("action")
            if action == "continue":
                bridge.approve()
            elif action == "cancel":
                bridge.cancel()

    except WebSocketDisconnect:
        logger.info("Debug WebSocket disconnected")

    except Exception as e:
        logger.error("Debug WebSocket error: {err}", err=str(e))

    finally:
        bridge.disconnect()
        poll_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await poll_task


async def _poll_and_run_jobs(websocket: WebSocket) -> None:
    """Poll for queued jobs and process them through the normal worker.

    Uses a single worker instance so the browser (via browser_manager)
    is reused across all jobs in this debug session.
    """
    worker = LinkedInWorker(db_session_factory=async_session)
    worker.running = True

    while bridge.is_active:
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(LinkedInScraperJob)
                    .where(LinkedInScraperJob.status == "queued")
                    .order_by(LinkedInScraperJob.created_at)
                    .limit(1)
                )
                job = result.scalar_one_or_none()

            if job and bridge.is_active:
                await bridge.log(
                    "info",
                    f"Job gefunden: #{job.id} {job.name} — starte Worker",
                )
                await worker._process_next_job()

        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error("Debug poll error: {err}", err=str(e))

        # Wait before polling again
        await asyncio.sleep(2)
