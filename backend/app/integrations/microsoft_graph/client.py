"""Thin Microsoft Graph HTTP client."""

from collections.abc import Mapping
from typing import Any

import httpx

from app.exceptions import ExternalServiceError

GRAPH_API_URL = "https://graph.microsoft.com/v1.0"


class MicrosoftGraphClient:
    """Small async wrapper around the Microsoft Graph REST API."""

    def __init__(self, access_token: str, *, timeout: float = 30.0) -> None:
        self.access_token = access_token
        self.timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def get(self, path: str, *, params: Mapping[str, Any] | None = None) -> dict:
        """Execute a GET request against Graph and return JSON."""
        return await self._request("GET", path, params=params)

    async def post(self, path: str, *, json: dict | None = None) -> dict:
        """Execute a POST request against Graph and return JSON if present."""
        return await self._request("POST", path, json=json)

    async def delete(self, path: str) -> None:
        """Execute a DELETE request against Graph."""
        await self._request("DELETE", path)

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{GRAPH_API_URL}/{path.lstrip('/')}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    url,
                    headers=self._headers,
                    **kwargs,
                )
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Microsoft Graph", str(exc)) from exc

        if response.is_error:
            raise ExternalServiceError(
                "Microsoft Graph",
                f"{response.status_code} {response.text[:300]}",
            )

        if response.status_code == 204 or not response.content:
            return {}
        return response.json()
