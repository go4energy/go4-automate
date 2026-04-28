"""Letterxpress.de v3 HTTP client.

Wraps the Letterxpress REST API for submitting print jobs, polling
job status, and reading account balance. The API expects every
request to contain an ``auth`` object with ``username``, ``apikey``,
and ``mode`` (``test`` or ``live``). Letters are uploaded as
base64-encoded PDFs together with an MD5 checksum of the base64
string.

Reference: LXP API v3 Dokumentation, Stand Dezember 2024.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Literal

import httpx
from loguru import logger

from app.exceptions import ExternalServiceError

DEFAULT_BASE_URL = "https://api.letterxpress.de/v3"
DEFAULT_TIMEOUT_SECONDS = 60.0
MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB per LXP docs

Mode = Literal["test", "live"]
Color = Literal["1", "4"]  # "1" = b/w, "4" = color CMYK
PrintMode = Literal["simplex", "duplex"]
Shipping = Literal["national", "international", "auto"]
Registered = Literal["r1", "r2"]  # r1 = Einschreiben Einwurf, r2 = Einschreiben
JobStatus = Literal["queue", "hold", "done", "canceled", "draft"]


@dataclass
class SubmitResult:
    """Outcome of POST /v3/printjobs."""

    job_id: int
    status: str  # "queue" / "draft" / "hold" / etc.
    pages: int
    amount_net: Decimal  # Netto-Preis in EUR (0.00 in Test-Mode)
    vat: Decimal
    address_line: str  # extracted by LXP from the PDF address window
    raw: dict[str, Any]


@dataclass
class JobInfo:
    """Outcome of GET /v3/printjobs/{id}."""

    job_id: int
    status: str
    shipping: str
    mode: str
    color: str
    pages: int
    amount_net: Decimal
    vat: Decimal
    address_line: str
    created_at: str
    updated_at: str
    raw: dict[str, Any]


@dataclass
class BalanceInfo:
    balance: Decimal
    currency: str


class LetterxpressError(ExternalServiceError):
    """Raised when the Letterxpress API returns an error."""

    def __init__(self, detail: str, *, status_code: int | None = None):
        super().__init__(service="Letterxpress", detail=detail)
        self.api_status_code = status_code


class LetterxpressClient:
    """Async Letterxpress v3 client."""

    def __init__(
        self,
        username: str,
        apikey: str,
        *,
        mode: Mode = "test",
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        if not username or not apikey:
            raise ValueError("Letterxpress-Username und API-Key sind Pflicht.")
        if mode not in ("test", "live"):
            raise ValueError(f"Ungültiger Letterxpress-Mode: {mode!r}")
        self._username = username
        self._apikey = apikey
        self._mode: Mode = mode
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def mode(self) -> Mode:
        return self._mode

    def _auth_payload(self) -> dict[str, str]:
        return {
            "username": self._username,
            "apikey": self._apikey,
            "mode": self._mode,
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
    ) -> dict:
        url = f"{self._base_url}{path}"
        body = json_body or {}
        body.setdefault("auth", self._auth_payload())
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.request(method, url, json=body)
            except httpx.HTTPError as exc:
                logger.error(
                    "Letterxpress {method} {url} failed: {err}",
                    method=method,
                    url=url,
                    err=str(exc),
                )
                raise LetterxpressError(f"HTTP-Fehler: {exc}") from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise LetterxpressError(
                f"Antwort kein JSON ({resp.status_code}): {resp.text[:200]}"
            ) from exc

        api_status = data.get("status")
        # LXP returns {"status": 200, ...} on success. Any other value
        # (including None/missing) is an error — they send {"message": "Unauthorized."}
        # without a status field on auth failures.
        if resp.status_code != 200 or api_status != 200:
            msg = data.get("message") or resp.text[:200]
            raise LetterxpressError(
                f"{method} {path} → {resp.status_code}/{api_status}: {msg}",
                status_code=api_status,
            )
        return data

    async def get_balance(self) -> BalanceInfo:
        """GET /v3/balance — Guthaben in EUR."""
        data = await self._request("GET", "/balance")
        d = data.get("data", {})
        return BalanceInfo(
            balance=Decimal(str(d.get("balance", "0"))),
            currency=str(d.get("currency", "EUR")),
        )

    async def get_price(
        self,
        *,
        pages: int,
        color: Color = "1",
        mode: PrintMode = "simplex",
        shipping: Shipping = "national",
        c4: int = 0,
        registered: Registered | None = None,
    ) -> Decimal:
        """GET /v3/price — Preisvorschau (netto, EUR)."""
        spec: dict[str, Any] = {
            "pages": pages,
            "color": color,
            "mode": mode,
            "shipping": shipping,
            "c4": c4,
        }
        body: dict[str, Any] = {"letter": {"specification": spec}}
        if registered:
            body["letter"]["registered"] = registered
        data = await self._request("GET", "/price", json_body=body)
        price = data.get("data", {}).get("price", "0")
        return Decimal(str(price))

    async def submit_letter(
        self,
        pdf_bytes: bytes,
        *,
        color: Color = "1",
        print_mode: PrintMode = "simplex",
        shipping: Shipping = "national",
        c4: int = 1,
        filename_original: str | None = None,
        registered: Registered | None = None,
        dispatch_date: date | None = None,
        notice: str | None = None,
    ) -> SubmitResult:
        """POST /v3/printjobs — Brief einreichen.

        ``pdf_bytes`` muss DIN A4 hochkant sein und die Empfängeradresse
        im DIN-5008 Sichtfenster (45-50mm von oben, 20mm von links)
        enthalten. Die API extrahiert die Adresse selbst aus dem PDF.
        """
        if not pdf_bytes:
            raise ValueError("PDF darf nicht leer sein.")
        if len(pdf_bytes) > MAX_PDF_SIZE_BYTES:
            raise ValueError(
                f"PDF zu groß ({len(pdf_bytes)} Bytes), Limit {MAX_PDF_SIZE_BYTES}."
            )

        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        checksum = hashlib.md5(b64.encode("utf-8")).hexdigest()

        letter: dict[str, Any] = {
            "base64_file": b64,
            "base64_file_checksum": checksum,
            "specification": {
                "color": color,
                "mode": print_mode,
                "shipping": shipping,
                "c4": c4,
            },
        }
        if filename_original:
            letter["filename_original"] = filename_original
        if registered:
            letter["registered"] = registered
        if dispatch_date:
            letter["dispatch_date"] = dispatch_date.isoformat()
        if notice:
            letter["notice"] = notice[:255]

        logger.info(
            "Letterxpress submit ({mode}): {bytes} bytes, color={color}, c4={c4}",
            mode=self._mode,
            bytes=len(pdf_bytes),
            color=color,
            c4=c4,
        )

        data = await self._request("POST", "/printjobs", json_body={"letter": letter})
        d = data.get("data", {})
        item = (d.get("items") or [{}])[0]
        return SubmitResult(
            job_id=int(d.get("id", 0)),
            status=str(d.get("status", "")),
            pages=int(item.get("pages", 0)),
            amount_net=Decimal(str(item.get("amount", "0"))),
            vat=Decimal(str(item.get("vat", "0"))),
            address_line=str(item.get("address", "")),
            raw=d,
        )

    async def get_job(self, job_id: int) -> JobInfo:
        """GET /v3/printjobs/{id}."""
        data = await self._request("GET", f"/printjobs/{job_id}")
        d = data.get("data", {})
        item = (d.get("items") or [{}])[0]
        return JobInfo(
            job_id=int(d.get("id", job_id)),
            status=str(d.get("status", "")),
            shipping=str(d.get("shipping", "")),
            mode=str(d.get("mode", "")),
            color=str(d.get("color", "")),
            pages=int(item.get("pages", 0)),
            amount_net=Decimal(str(item.get("amount", "0"))),
            vat=Decimal(str(item.get("vat", "0"))),
            address_line=str(item.get("address", "")),
            created_at=str(d.get("created_at", "")),
            updated_at=str(d.get("updated_at", "")),
            raw=d,
        )

    async def list_jobs(self, *, filter_status: JobStatus | None = None) -> list[dict]:
        """GET /v3/printjobs[?filter=...]."""
        path = "/printjobs"
        if filter_status:
            path = f"{path}?filter={filter_status}"
        data = await self._request("GET", path)
        return data.get("data", {}).get("printjobs", [])

    async def delete_job(self, job_id: int) -> None:
        """DELETE /v3/printjobs/{id} — geht nur in den ersten 15 Minuten und
        wenn der Job noch nicht ``done`` ist."""
        await self._request("DELETE", f"/printjobs/{job_id}")
