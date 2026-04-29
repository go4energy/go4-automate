"""Tests for the Letter worker.

Stubs Letterxpress HTTP via httpx.MockTransport so no real submissions
go to the provider, then exercises the full worker pipeline (load
contact → render PDF → submit → update Letter + PendingAction).
"""

from __future__ import annotations

import json

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.models import Company, Contact
from app.engagement.models import (
    EngagementPipeline,
    PendingAction,
    PipelineEnrollment,
)
from app.letter.models import Letter, LetterStatus, LetterTemplate
from app.letter.settings_service import (
    ensure_module_parameters,
    set_letter_setting,
)
from app.letter.worker import (
    process_letter_actions,
    sync_pending_letter_statuses,
)

TENANT = "test-tenant"


# ============== Fixtures ==============


def _patch_async_client(monkeypatch, handler):
    """Force httpx.AsyncClient to use the given mock handler everywhere."""
    transport = httpx.MockTransport(handler)
    real_init = httpx.AsyncClient.__init__

    def fake_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", fake_init)


@pytest.fixture
def lxp_handler():
    """Default Letterxpress mock — submit succeeds, balance = 99 EUR, get_job ready."""
    captured = {"submits": [], "balances": 0, "jobs_get": []}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        body = json.loads(request.content.decode()) if request.content else {}

        if path.endswith("/v3/balance"):
            captured["balances"] += 1
            return httpx.Response(200, json={
                "status": 200, "message": "OK",
                "data": {"balance": 99.50, "currency": "EUR"},
            })

        if path.endswith("/v3/printjobs") and request.method == "POST":
            captured["submits"].append(body)
            return httpx.Response(200, json={
                "status": 200, "message": "OK",
                "data": {
                    "id": 9999, "status": "queue",
                    "shipping": "national", "mode": "simplex", "color": "4",
                    "items": [{
                        "address": "Max Mustermann, Musterstr. 1, 12345 Stadt",
                        "pages": 1, "amount": 0.0, "vat": 0.0, "status": "queue",
                    }],
                },
            })

        if "/v3/printjobs/" in path and request.method == "GET":
            job_id = path.rsplit("/", 1)[-1]
            captured["jobs_get"].append(job_id)
            return httpx.Response(200, json={
                "status": 200, "message": "OK",
                "data": {
                    "id": int(job_id), "status": "done",
                    "shipping": "national", "mode": "simplex", "color": "4",
                    "created_at": "2026-04-29 09:00:00",
                    "updated_at": "2026-04-29 09:30:00",
                    "items": [{"address": "X", "pages": 1, "amount": 0.0,
                               "vat": 0.0, "status": "sent"}],
                },
            })

        return httpx.Response(404, json={"message": "Not found"})

    return handler, captured


async def _seed_credentials(db: AsyncSession) -> None:
    await ensure_module_parameters(db, TENANT)
    await set_letter_setting(db, TENANT, "letterxpress_username", "u")
    await set_letter_setting(db, TENANT, "letterxpress_apikey", "k")
    await set_letter_setting(db, TENANT, "letterxpress_default_mode", "test")


async def _seed_contact_with_address(db: AsyncSession) -> Contact:
    company = Company(
        tenant_id=TENANT,
        name="ACME GmbH",
        address={"street": "Musterstr. 1", "zip": "12345", "city": "Musterstadt", "country": "DE"},
    )
    db.add(company)
    await db.flush()

    contact = Contact(
        tenant_id=TENANT,
        email="max@example.com",
        name="Max Mustermann",
        position="Geschäftsführer",
        company_id=company.id,
    )
    db.add(contact)
    await db.flush()
    return contact


async def _seed_template(db: AsyncSession) -> LetterTemplate:
    template = LetterTemplate(
        tenant_id=TENANT,
        name="Standard",
        format="a4",
        content_html="dummy",
        is_active=True,
    )
    db.add(template)
    await db.flush()
    return template


async def _seed_pipeline(db: AsyncSession, contact: Contact) -> tuple[EngagementPipeline, PipelineEnrollment]:
    # Skip the tenant FK by inserting via raw — SQLite test schema may not have
    # a tenant fixture. We fall back to nothing if FK fails.
    pipeline = EngagementPipeline(
        tenant_id=TENANT,
        name="Letter test pipeline",
        slug="letter-test",
        channels=["letter"],
    )
    db.add(pipeline)
    await db.flush()
    enrollment = PipelineEnrollment(
        tenant_id=TENANT,
        pipeline_id=pipeline.id,
        contact_id=contact.id,
    )
    db.add(enrollment)
    await db.flush()
    return pipeline, enrollment


async def _seed_action(
    db: AsyncSession,
    contact: Contact,
    pipeline: EngagementPipeline,
    enrollment: PipelineEnrollment,
    template: LetterTemplate,
    *,
    body: str = "<p>Sehr geehrter Herr Mustermann,</p><p>Test-Inhalt.</p>",
    status: str = "approved",
    needs_approval: bool = False,
) -> PendingAction:
    action = PendingAction(
        tenant_id=TENANT,
        contact_id=contact.id,
        pipeline_id=pipeline.id,
        enrollment_id=enrollment.id,
        module="letter",
        action_type="send_letter",
        suggested_content=body,
        context={"template_key": template.id},
        status=status,
        needs_approval=needs_approval,
    )
    db.add(action)
    await db.flush()
    return action


# ============== Tests ==============


@pytest.mark.asyncio
async def test_worker_skips_when_credentials_missing(db_session: AsyncSession):
    await ensure_module_parameters(db_session, TENANT)
    # No username/apikey set
    stats = await process_letter_actions(db_session, TENANT)
    assert stats.picked == 0
    assert stats.succeeded == 0


@pytest.mark.asyncio
async def test_worker_processes_approved_action(monkeypatch, lxp_handler, db_session: AsyncSession):
    handler, captured = lxp_handler
    _patch_async_client(monkeypatch, handler)

    await _seed_credentials(db_session)
    contact = await _seed_contact_with_address(db_session)
    template = await _seed_template(db_session)
    pipeline, enrollment = await _seed_pipeline(db_session, contact)
    action = await _seed_action(db_session, contact, pipeline, enrollment, template)

    stats = await process_letter_actions(db_session, TENANT)
    assert stats.picked == 1
    assert stats.succeeded == 1
    assert stats.failed == 0

    # PendingAction completed
    await db_session.refresh(action)
    assert action.status == "completed"
    assert action.result is not None
    assert action.result["letterxpress_job_id"] == "9999"

    # Letter created with provider data
    from sqlalchemy import select
    letter_q = await db_session.execute(
        select(Letter).where(Letter.pending_action_id == action.id)
    )
    letter = letter_q.scalar_one()
    assert letter.status == LetterStatus.SENT
    assert letter.letterxpress_job_id == "9999"
    assert letter.send_mode == "test"
    assert letter.recipient_name == "Max Mustermann"
    assert letter.recipient_company == "ACME GmbH"
    assert letter.recipient_zip == "12345"
    assert letter.pdf_path  # file got written

    # Letterxpress was actually called
    assert len(captured["submits"]) == 1
    submitted = captured["submits"][0]
    assert submitted["auth"]["username"] == "u"
    assert submitted["auth"]["mode"] == "test"
    assert submitted["letter"]["specification"]["color"] == "4"


@pytest.mark.asyncio
async def test_worker_skips_pending_actions_that_need_approval(
    monkeypatch, lxp_handler, db_session: AsyncSession
):
    handler, _ = lxp_handler
    _patch_async_client(monkeypatch, handler)

    await _seed_credentials(db_session)
    contact = await _seed_contact_with_address(db_session)
    template = await _seed_template(db_session)
    pipeline, enrollment = await _seed_pipeline(db_session, contact)
    await _seed_action(
        db_session, contact, pipeline, enrollment, template,
        status="pending", needs_approval=True,
    )

    stats = await process_letter_actions(db_session, TENANT)
    # picked includes pending+needs_approval but they get filtered out
    assert stats.succeeded == 0


@pytest.mark.asyncio
async def test_worker_handles_pending_with_auto_approval(
    monkeypatch, lxp_handler, db_session: AsyncSession
):
    handler, _ = lxp_handler
    _patch_async_client(monkeypatch, handler)

    await _seed_credentials(db_session)
    contact = await _seed_contact_with_address(db_session)
    template = await _seed_template(db_session)
    pipeline, enrollment = await _seed_pipeline(db_session, contact)
    await _seed_action(
        db_session, contact, pipeline, enrollment, template,
        status="pending", needs_approval=False,
    )

    stats = await process_letter_actions(db_session, TENANT)
    assert stats.succeeded == 1


@pytest.mark.asyncio
async def test_worker_marks_action_failed_when_address_missing(
    monkeypatch, lxp_handler, db_session: AsyncSession
):
    handler, _ = lxp_handler
    _patch_async_client(monkeypatch, handler)

    await _seed_credentials(db_session)
    # Contact without company → no address
    contact = Contact(
        tenant_id=TENANT, email="x@example.com", name="X",
    )
    db_session.add(contact)
    await db_session.flush()
    template = await _seed_template(db_session)
    pipeline, enrollment = await _seed_pipeline(db_session, contact)
    action = await _seed_action(db_session, contact, pipeline, enrollment, template)

    stats = await process_letter_actions(db_session, TENANT)
    assert stats.failed == 1
    await db_session.refresh(action)
    assert action.status == "failed"
    assert "Empfängeradresse" in (action.error_message or "")


@pytest.mark.asyncio
async def test_worker_uses_send_mode_override_from_context(
    monkeypatch, lxp_handler, db_session: AsyncSession
):
    handler, captured = lxp_handler
    _patch_async_client(monkeypatch, handler)

    await _seed_credentials(db_session)
    contact = await _seed_contact_with_address(db_session)
    template = await _seed_template(db_session)
    pipeline, enrollment = await _seed_pipeline(db_session, contact)

    action = PendingAction(
        tenant_id=TENANT,
        contact_id=contact.id,
        pipeline_id=pipeline.id,
        enrollment_id=enrollment.id,
        module="letter",
        action_type="send_letter",
        suggested_content="<p>Hi.</p>",
        context={"template_key": template.id, "send_mode": "live"},
        status="approved",
        needs_approval=False,
    )
    db_session.add(action)
    await db_session.flush()

    await process_letter_actions(db_session, TENANT)
    assert captured["submits"][0]["auth"]["mode"] == "live"


@pytest.mark.asyncio
async def test_status_sync_marks_done_letters_as_delivered(
    monkeypatch, lxp_handler, db_session: AsyncSession
):
    handler, captured = lxp_handler
    _patch_async_client(monkeypatch, handler)

    await _seed_credentials(db_session)
    contact = await _seed_contact_with_address(db_session)
    template = await _seed_template(db_session)

    letter = Letter(
        tenant_id=TENANT,
        template_id=template.id,
        contact_id=contact.id,
        recipient_name="Max",
        recipient_company="ACME",
        recipient_street="Str. 1",
        recipient_zip="12345",
        recipient_city="Stadt",
        content_html="<p>x</p>",
        status=LetterStatus.SENT,
        send_mode="test",
        letterxpress_job_id="9999",
        provider_status="queue",
    )
    db_session.add(letter)
    await db_session.flush()

    counts = await sync_pending_letter_statuses(db_session, TENANT)
    assert counts["checked"] == 1
    assert counts["delivered"] == 1

    await db_session.refresh(letter)
    assert letter.status == LetterStatus.DELIVERED
    assert letter.provider_status == "done"
    assert letter.delivered_at is not None
