"""Thin Microsoft Graph HTTP client."""

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

from app.exceptions import ExternalServiceError

GRAPH_API_URL = "https://graph.microsoft.com/v1.0"


class MicrosoftGraphClient:
    """Small async wrapper around the Microsoft Graph REST API."""

    def __init__(
        self,
        access_token: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.access_token = access_token
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict:
        """Execute a GET request against Graph and return JSON."""
        return await self._request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        *,
        json: dict | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict:
        """Execute a POST request against Graph and return JSON if present."""
        return await self._request("POST", path, json=json, headers=headers)

    async def patch(
        self,
        path: str,
        *,
        json: dict | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict:
        """Execute a PATCH request against Graph and return JSON if present."""
        return await self._request("PATCH", path, json=json, headers=headers)

    async def delete(self, path: str) -> None:
        """Execute a DELETE request against Graph."""
        await self._request("DELETE", path)

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{GRAPH_API_URL}/{path.lstrip('/')}"
        extra_headers = kwargs.pop("headers", None) or {}
        headers = {**self._headers, **dict(extra_headers)}
        attempt = 0
        while True:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=headers,
                        **kwargs,
                    )
            except httpx.HTTPError as exc:
                if attempt >= self.max_retries:
                    raise ExternalServiceError("Microsoft Graph", str(exc)) from exc
                await asyncio.sleep(min(2**attempt, 5))
                attempt += 1
                continue

            if response.status_code in {429, 503, 504} and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else min(2**attempt, 5)
                except ValueError:
                    delay = min(2**attempt, 5)
                await asyncio.sleep(delay)
                attempt += 1
                continue

            if response.is_error:
                raise ExternalServiceError(
                    "Microsoft Graph",
                    f"{response.status_code} {response.text[:300]}",
                )
            break

        if response.status_code == 204 or not response.content:
            return {}
        return response.json()
