"""Auth system tests — login, users, groups, permissions."""

import pytest

HEADERS = {"X-Tenant-ID": "test-tenant"}

ADMIN_USER = {
    "email": "admin@test.com",
    "password": "admin123",
    "display_name": "Test Admin",
    "role": "admin",
}

REGULAR_USER = {
    "email": "user@test.com",
    "password": "user1234",
    "display_name": "Regular User",
    "role": "user",
}


# --- Login ---


@pytest.mark.anyio
async def test_login_success(client, test_tenant):
    """POST /api/v1/auth/login with valid credentials returns a token."""
    # Create a user first
    await client.post("/api/v1/auth/users", json=ADMIN_USER, headers=HEADERS)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_USER["email"], "password": ADMIN_USER["password"]},
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == ADMIN_USER["email"]


@pytest.mark.anyio
async def test_login_wrong_password(client, test_tenant):
    """POST /api/v1/auth/login with wrong password returns 401."""
    await client.post("/api/v1/auth/users", json=ADMIN_USER, headers=HEADERS)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_USER["email"], "password": "wrong"},
        headers=HEADERS,
    )
    assert response.status_code == 401


# --- Users CRUD ---


@pytest.mark.anyio
async def test_create_user(client, test_tenant):
    """POST /api/v1/auth/users creates a new user."""
    response = await client.post(
        "/api/v1/auth/users", json=REGULAR_USER, headers=HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == REGULAR_USER["email"]
    assert data["role"] == "user"
    assert data["active"] is True


@pytest.mark.anyio
async def test_list_users(client, test_tenant):
    """GET /api/v1/auth/users returns all users."""
    await client.post("/api/v1/auth/users", json=ADMIN_USER, headers=HEADERS)
    await client.post("/api/v1/auth/users", json=REGULAR_USER, headers=HEADERS)

    response = await client.get("/api/v1/auth/users", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_update_user(client, test_tenant):
    """PUT /api/v1/auth/users/{id} updates user fields."""
    create_resp = await client.post(
        "/api/v1/auth/users", json=REGULAR_USER, headers=HEADERS
    )
    user_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/auth/users/{user_id}",
        json={"display_name": "Updated Name"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "Updated Name"


@pytest.mark.anyio
async def test_delete_user(client, test_tenant):
    """DELETE /api/v1/auth/users/{id} deactivates the user."""
    create_resp = await client.post(
        "/api/v1/auth/users", json=REGULAR_USER, headers=HEADERS
    )
    user_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/auth/users/{user_id}", headers=HEADERS)
    assert response.status_code == 204

    # User should now be inactive
    get_resp = await client.get(f"/api/v1/auth/users/{user_id}", headers=HEADERS)
    assert get_resp.json()["active"] is False


@pytest.mark.anyio
async def test_duplicate_email(client, test_tenant):
    """POST /api/v1/auth/users with duplicate email returns 409."""
    await client.post("/api/v1/auth/users", json=ADMIN_USER, headers=HEADERS)
    response = await client.post("/api/v1/auth/users", json=ADMIN_USER, headers=HEADERS)
    assert response.status_code == 409


# --- Groups CRUD ---


@pytest.mark.anyio
async def test_create_group(client, test_tenant):
    """POST /api/v1/auth/groups creates a new group."""
    group = {
        "name": "Redakteure",
        "description": "Content-Redakteure",
        "permissions": {
            "collector": {
                "view": True,
                "edit": True,
                "delete": False,
                "settings": False,
            },
            "creator": {"view": True, "edit": True, "delete": False, "settings": False},
        },
    }
    response = await client.post("/api/v1/auth/groups", json=group, headers=HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Redakteure"
    assert data["permissions"]["collector"]["view"] is True


@pytest.mark.anyio
async def test_add_user_to_group(client, test_tenant):
    """POST /api/v1/auth/groups/{id}/users/{user_id} adds user to group."""
    user_resp = await client.post(
        "/api/v1/auth/users", json=REGULAR_USER, headers=HEADERS
    )
    user_id = user_resp.json()["id"]

    group_resp = await client.post(
        "/api/v1/auth/groups",
        json={"name": "Editors", "permissions": {}},
        headers=HEADERS,
    )
    group_id = group_resp.json()["id"]

    response = await client.post(
        f"/api/v1/auth/groups/{group_id}/users/{user_id}", headers=HEADERS
    )
    assert response.status_code == 204


# --- Me & Password ---


@pytest.mark.anyio
async def test_get_me(client, test_tenant):
    """GET /api/v1/auth/me returns current user with resolved permissions."""
    # Create user and login to get token
    await client.post("/api/v1/auth/users", json=ADMIN_USER, headers=HEADERS)
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_USER["email"], "password": ADMIN_USER["password"]},
        headers=HEADERS,
    )
    token = login_resp.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={**HEADERS, "Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == ADMIN_USER["email"]
    assert data["role"] == "admin"
    # Admin should have all permissions
    assert data["resolved_permissions"]["collector"]["view"] is True


@pytest.mark.anyio
async def test_reset_password(client, test_tenant):
    """PUT /api/v1/auth/users/{id}/reset-password resets user password."""
    create_resp = await client.post(
        "/api/v1/auth/users", json=REGULAR_USER, headers=HEADERS
    )
    user_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/auth/users/{user_id}/reset-password",
        json={"new_password": "newpassword123"},
        headers=HEADERS,
    )
    assert response.status_code == 200

    # Login with new password should work
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": REGULAR_USER["email"], "password": "newpassword123"},
        headers=HEADERS,
    )
    assert login_resp.status_code == 200


# --- Permission Schema ---


@pytest.mark.anyio
async def test_permission_schema(client, test_tenant):
    """GET /api/v1/auth/permissions/schema returns module/action matrix."""
    response = await client.get("/api/v1/auth/permissions/schema", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "modules" in data
    assert "collector" in data["modules"]
    assert "view" in data["modules"]["collector"]


# --- Auth Middleware ---


@pytest.mark.anyio
async def test_middleware_blocks_unauthenticated(test_tenant):
    """API calls without auth should be blocked by middleware."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as unauthenticated:
        response = await unauthenticated.get(
            "/api/v1/modules", headers={"X-Tenant-ID": "test-tenant"}
        )
        assert response.status_code == 401


@pytest.mark.anyio
async def test_middleware_requires_tenant_header_for_protected_routes(test_tenant):
    """Protected tenant-scoped routes should reject requests without X-Tenant-ID."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as raw_client:
        response = await raw_client.get(
            "/api/v1/modules", headers={"X-Backend-Secret": "wrong-secret"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "X-Tenant-ID Header fehlt"


@pytest.mark.anyio
async def test_login_requires_tenant_header(test_tenant):
    """Login should require explicit tenant context before auth logic runs."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as raw_client:
        response = await raw_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "secret"},
            headers={"X-Backend-Secret": "wrong-secret"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "X-Tenant-ID Header fehlt"


@pytest.mark.anyio
async def test_oauth_callbacks_are_exempt_from_tenant_header_requirement(test_tenant):
    """OAuth callbacks must be reachable without tenant header because providers don't send one."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as raw_client:
        response = await raw_client.get(
            "/api/v1/briefing/personal/oauth/callback?code=test&state=test"
        )
        assert response.status_code != 400
        assert "X-Tenant-ID Header fehlt" not in response.text
