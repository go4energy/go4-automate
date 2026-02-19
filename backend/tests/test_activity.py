"""Activity log tests."""

import pytest

HEADERS = {"X-Tenant-ID": "test-tenant"}


@pytest.mark.anyio
async def test_list_activities_empty(client, test_tenant):
    """GET /api/v1/activities should return empty list."""
    response = await client.get("/api/v1/activities", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_activities_after_log(client, test_tenant, db_session):
    """Activities should appear after being logged."""
    from app.services.activity import ActivityService

    service = ActivityService(db_session)
    await service.log(
        "test-tenant",
        "content",
        "content.generated",
        "Test post generiert",
        severity="success",
    )
    await db_session.commit()

    response = await client.get("/api/v1/activities", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["module"] == "content"
    assert data[0]["action"] == "content.generated"
    assert data[0]["severity"] == "success"


@pytest.mark.anyio
async def test_filter_by_module(client, test_tenant, db_session):
    """Activities can be filtered by module."""
    from app.services.activity import ActivityService

    service = ActivityService(db_session)
    await service.log("test-tenant", "content", "content.generated", "Content 1")
    await service.log("test-tenant", "research", "research.run", "Research 1")
    await db_session.commit()

    response = await client.get(
        "/api/v1/activities",
        params={"module": "content"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["module"] == "content"


@pytest.mark.anyio
async def test_activity_limit_and_offset(client, test_tenant, db_session):
    """Activities support pagination via limit and offset."""
    from app.services.activity import ActivityService

    service = ActivityService(db_session)
    for i in range(5):
        await service.log("test-tenant", "content", "test", f"Activity {i}")
    await db_session.commit()

    response = await client.get(
        "/api/v1/activities",
        params={"limit": 2, "offset": 0},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert len(response.json()) == 2

    response2 = await client.get(
        "/api/v1/activities",
        params={"limit": 2, "offset": 3},
        headers=HEADERS,
    )
    assert response2.status_code == 200
    assert len(response2.json()) == 2


@pytest.mark.anyio
async def test_activity_stats_empty(client, test_tenant):
    """GET /api/v1/activities/stats should return empty list."""
    response = await client.get("/api/v1/activities/stats", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_activity_stats(client, test_tenant, db_session):
    """Stats should aggregate by module and action."""
    from app.services.activity import ActivityService

    service = ActivityService(db_session)
    await service.log("test-tenant", "content", "content.generated", "A")
    await service.log("test-tenant", "content", "content.generated", "B")
    await service.log("test-tenant", "content", "content.published", "C")
    await service.log("test-tenant", "research", "research.run", "D")
    await db_session.commit()

    response = await client.get(
        "/api/v1/activities/stats",
        params={"days": 7},
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    content_stats = next(s for s in data if s["module"] == "content")
    assert content_stats["total"] == 3
    assert content_stats["actions"]["content.generated"] == 2
    assert content_stats["actions"]["content.published"] == 1


@pytest.mark.anyio
async def test_activity_tenant_isolation(client, test_tenant, db_session):
    """Activities should be isolated per tenant."""
    from app.services.activity import ActivityService

    service = ActivityService(db_session)
    await service.log("test-tenant", "content", "test", "My activity")
    await db_session.commit()

    response = await client.get(
        "/api/v1/activities",
        headers={"X-Tenant-ID": "other-tenant"},
    )
    assert response.status_code == 200
    assert response.json() == []
