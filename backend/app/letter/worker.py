"""Letter worker — consumes PendingActions and submits letters via Letterxpress.

Picks up engagement PendingActions with ``module="letter"`` and a status
that's ready to be acted on (``approved`` always; ``pending`` only when
``needs_approval=False``). For each action:

1. Loads the contact + company so the address is available.
2. Materialises a Letter row with recipient + body from the action.
3. Renders the PDF via the pdf_renderer (with the tenant's letterhead).
4. Submits the PDF to Letterxpress in the configured mode (test/live).
5. Updates the Letter with provider job id, status, cost.
6. Logs a ContactActivity on channel="letter".
7. Marks the PendingAction completed (or failed on errors).

Run manually — never on a hands-off cron — with ``run_letter_worker.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.models import Contact
from app.engagement.activity_helper import Channel, Direction, log_activity
from app.engagement.models import PendingAction
from app.letter.letterxpress_client import LetterxpressError
from app.letter.models import Letter, LetterStatus, LetterTemplate
from app.letter.pdf_renderer import PdfRendererError, render_letter_pdf
from app.letter.settings_service import (
    LetterSettingsError,
    get_letter_settings,
    get_letterxpress_client,
)

LETTER_MODULE = "letter"
ACTION_TYPE = "send_letter"

OUTPUT_BASE = Path("data/letter")  # data/letter/{tenant}/letters/{letter_id}.pdf


@dataclass
class WorkerStats:
    picked: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


async def _select_actions(
    db: AsyncSession,
    tenant_id: str,
    *,
    limit: int,
) -> list[PendingAction]:
    """Pick up actionable letter PendingActions.

    Approved actions always qualify. Pending actions qualify only when
    ``needs_approval=False`` (auto-actions). Already-completed/failed
    actions are skipped.
    """
    q = (
        select(PendingAction)
        .where(
            PendingAction.tenant_id == tenant_id,
            PendingAction.module == LETTER_MODULE,
            PendingAction.status.in_(("approved", "pending")),
        )
        .order_by(PendingAction.created_at.asc())
        .limit(limit)
    )
    result = await db.execute(q)
    actions = list(result.scalars().all())
    # Filter out pending actions that still need approval
    return [
        a
        for a in actions
        if a.status == "approved" or (a.status == "pending" and not a.needs_approval)
    ]


async def _load_contact(db: AsyncSession, contact_id: int) -> Contact | None:
    r = await db.execute(
        select(Contact)
        .options(selectinload(Contact.company))
        .where(Contact.id == contact_id)
    )
    return r.scalar_one_or_none()


async def _resolve_template(
    db: AsyncSession,
    tenant_id: str,
    template_key: int | str | None,
) -> LetterTemplate | None:
    """Find the template referenced by the action's context.

    ``template_key`` can be an integer id or a stringified id. Falls
    back to the most recently created active template if not given.
    """
    q = select(LetterTemplate).where(LetterTemplate.tenant_id == tenant_id)
    if template_key is not None:
        try:
            q = q.where(LetterTemplate.id == int(template_key))
        except (TypeError, ValueError):
            return None
    else:
        q = q.where(LetterTemplate.is_active.is_(True)).order_by(
            LetterTemplate.created_at.desc()
        )
    r = await db.execute(q.limit(1))
    return r.scalar_one_or_none()


def _build_recipient_kwargs(
    contact: Contact,
    address_override: dict[str, str] | None = None,
) -> dict[str, str | None]:
    """Build the recipient_* kwargs for a Letter from a contact + optional override."""
    company_name = contact.company.name if contact.company else None
    addr = (contact.company.address if contact.company else None) or {}
    if address_override:
        addr = {**addr, **{k: v for k, v in address_override.items() if v}}

    return {
        "recipient_name": contact.name,
        "recipient_company": company_name,
        "recipient_street": addr.get("street"),
        "recipient_zip": addr.get("zip") or addr.get("postal_code"),
        "recipient_city": addr.get("city"),
        "recipient_country": (addr.get("country") or "DE").upper(),
    }


def _save_pdf(pdf_bytes: bytes, tenant_id: str, letter_id: int) -> str:
    out_dir = OUTPUT_BASE / tenant_id / "letters"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"letter_{letter_id}.pdf"
    out_path.write_bytes(pdf_bytes)
    return str(out_path)


async def _create_or_get_letter(
    db: AsyncSession,
    tenant_id: str,
    *,
    action: PendingAction,
    template: LetterTemplate,
    contact: Contact,
    send_mode: str,
) -> Letter:
    """Materialise the Letter row from the action context."""
    address_override = (action.context or {}).get("recipient_address") or {}
    recipient = _build_recipient_kwargs(contact, address_override)

    letter = Letter(
        tenant_id=tenant_id,
        template_id=template.id,
        contact_id=contact.id,
        pipeline_id=action.pipeline_id,
        pending_action_id=action.id,
        content_html=action.suggested_content or "",
        status=LetterStatus.QUEUED,
        send_mode=send_mode,
        queued_at=datetime.now(UTC),
        **recipient,
    )
    db.add(letter)
    await db.flush()  # need letter.id
    return letter


def _action_send_mode(action: PendingAction, default: str) -> str:
    """Pick the per-action send_mode override from context, falling back to tenant default."""
    ctx_mode = (action.context or {}).get("send_mode")
    if ctx_mode in ("test", "live"):
        return ctx_mode
    return default


async def process_letter_actions(
    db: AsyncSession,
    tenant_id: str,
    *,
    limit: int = 50,
) -> WorkerStats:
    """Main entry point: pick up letter actions and send them.

    Caller is responsible for committing the AsyncSession after this
    returns. Each individual letter is flushed but not committed,
    so a single batch is one transactional unit (errors abort the whole
    batch — that's fine since each Letter creation is independent).
    """
    stats = WorkerStats()

    settings = await get_letter_settings(db, tenant_id)
    if not settings.is_complete:
        logger.warning(
            "Letter worker: skipping tenant {t} — credentials not configured",
            t=tenant_id,
        )
        return stats

    actions = await _select_actions(db, tenant_id, limit=limit)
    stats.picked = len(actions)
    if not actions:
        return stats

    for action in actions:
        try:
            await _process_one(db, tenant_id, action, default_mode=settings.mode)
            stats.succeeded += 1
        except LetterSettingsError as exc:
            stats.failed += 1
            stats.errors.append(f"action {action.id}: {exc.message}")
            await _mark_action_failed(action, str(exc.message), db=db)
        except (PdfRendererError, LetterxpressError) as exc:
            stats.failed += 1
            stats.errors.append(f"action {action.id}: {exc}")
            await _mark_action_failed(action, str(exc), db=db)
        except Exception as exc:
            logger.exception(
                "Letter worker unexpected error on action {id}", id=action.id
            )
            stats.failed += 1
            stats.errors.append(f"action {action.id}: {exc}")
            await _mark_action_failed(action, f"unerwarteter Fehler: {exc}", db=db)

    return stats


async def _process_one(
    db: AsyncSession,
    tenant_id: str,
    action: PendingAction,
    *,
    default_mode: str,
) -> None:
    """Fully process a single PendingAction. Raises on any handled failure."""
    if action.action_type != ACTION_TYPE:
        raise LetterSettingsError(
            f"unsupported action_type {action.action_type!r} on letter module"
        )

    contact = await _load_contact(db, action.contact_id)
    if contact is None:
        raise LetterSettingsError(f"Contact {action.contact_id} nicht gefunden")

    template = await _resolve_template(
        db, tenant_id, (action.context or {}).get("template_key")
    )
    if template is None:
        raise LetterSettingsError(
            "Kein Letter-Template gefunden — bitte mindestens eines anlegen."
        )

    send_mode = _action_send_mode(action, default_mode)
    letter = await _create_or_get_letter(
        db,
        tenant_id,
        action=action,
        template=template,
        contact=contact,
        send_mode=send_mode,
    )

    pdf_bytes = render_letter_pdf(letter, template, tenant_id=tenant_id)
    letter.pdf_path = _save_pdf(pdf_bytes, tenant_id, letter.id)

    client = await get_letterxpress_client(db, tenant_id, override_mode=send_mode)
    submit = await client.submit_letter(
        pdf_bytes,
        color="4",  # color default; per-template/per-letter override possible later
        c4=1,
        filename_original=f"letter_{letter.id}.pdf",
    )

    letter.letterxpress_job_id = str(submit.job_id)
    letter.provider_status = submit.status
    # provider_cost_cents stored as net amount × 100 (test mode reports 0)
    letter.provider_cost_cents = int(round(float(submit.amount_net) * 100))
    letter.provider_synced_at = datetime.now(UTC)
    letter.status = LetterStatus.SENT
    letter.sent_at = datetime.now(UTC)
    letter.updated_at = datetime.now(UTC)

    # Log activity for the engagement timeline
    try:
        await log_activity(
            db=db,
            tenant_id=tenant_id,
            contact_id=contact.id,
            channel=Channel.LETTER,
            activity_type="letter_sent",
            direction=Direction.OUTBOUND,
            subject=f"Brief versendet: {letter.recipient_name}",
            content=(letter.content_html or "")[:500],
            source_module=LETTER_MODULE,
            pipeline_id=action.pipeline_id,
            metadata={
                "letter_id": letter.id,
                "letterxpress_job_id": letter.letterxpress_job_id,
                "send_mode": send_mode,
                "cost_cents": letter.provider_cost_cents,
            },
            commit=False,
        )
    except Exception as exc:
        logger.warning(
            "Letter worker: activity log failed for letter {lid}: {err}",
            lid=letter.id,
            err=str(exc),
        )

    action.status = "completed"
    action.completed_at = datetime.now(UTC)
    action.result = _build_action_result(letter, submit)
    await db.flush()

    logger.info(
        "Letter sent: tenant={t} action={a} letter={l} job={j} mode={m} cost_cents={c}",
        t=tenant_id,
        a=action.id,
        l=letter.id,
        j=letter.letterxpress_job_id,
        m=send_mode,
        c=letter.provider_cost_cents,
    )


def _build_action_result(letter: Letter, submit: Any) -> dict:
    return {
        "letter_id": letter.id,
        "letterxpress_job_id": letter.letterxpress_job_id,
        "send_mode": letter.send_mode,
        "provider_status": letter.provider_status,
        "provider_cost_cents": letter.provider_cost_cents,
        "amount_net_eur": str(submit.amount_net),
        "address_line": submit.address_line,
    }


async def _mark_action_failed(
    action: PendingAction,
    message: str,
    *,
    db: AsyncSession | None = None,
) -> None:
    action.status = "failed"
    action.error_message = message[:1000]
    action.completed_at = datetime.now(UTC)
    if db is not None:
        await db.flush()


# ============== Status sync ==============


async def sync_pending_letter_statuses(
    db: AsyncSession,
    tenant_id: str,
    *,
    limit: int = 200,
) -> dict[str, int]:
    """Poll Letterxpress for current job status of letters that aren't done yet.

    Letters with no job id, or already in DELIVERED/RETURNED/FAILED state
    are skipped. Updates ``provider_status`` + ``status`` + ``delivered_at``.
    """
    q = (
        select(Letter)
        .where(
            Letter.tenant_id == tenant_id,
            Letter.letterxpress_job_id.isnot(None),
            Letter.status.in_((LetterStatus.SENT, LetterStatus.QUEUED)),
        )
        .order_by(Letter.sent_at.asc())
        .limit(limit)
    )
    rows = (await db.execute(q)).scalars().all()
    counts = {"checked": 0, "updated": 0, "delivered": 0, "errors": 0}
    if not rows:
        return counts

    try:
        client = await get_letterxpress_client(db, tenant_id)
    except LetterSettingsError as exc:
        logger.warning("Status sync skipped — {err}", err=exc.message)
        return counts

    for letter in rows:
        counts["checked"] += 1
        try:
            info = await client.get_job(int(letter.letterxpress_job_id))
        except LetterxpressError as exc:
            counts["errors"] += 1
            logger.warning(
                "Status sync failed for letter {lid} job={j}: {err}",
                lid=letter.id,
                j=letter.letterxpress_job_id,
                err=str(exc),
            )
            continue

        new_provider_status = info.status
        if new_provider_status != letter.provider_status:
            letter.provider_status = new_provider_status
            counts["updated"] += 1

        # Map LXP status to our LetterStatus
        if new_provider_status == "done":
            letter.status = LetterStatus.DELIVERED
            letter.delivered_at = datetime.now(UTC)
            counts["delivered"] += 1
        elif new_provider_status == "canceled":
            letter.status = LetterStatus.RETURNED
            letter.return_reason = "Provider canceled"

        letter.provider_synced_at = datetime.now(UTC)

    await db.flush()
    return counts
