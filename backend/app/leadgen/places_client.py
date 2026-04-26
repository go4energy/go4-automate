"""Google Places API (New) client for Text Search.

Docs: https://developers.google.com/maps/documentation/places/web-service/text-search

Important:
- Auth is via X-Goog-Api-Key header (no OAuth needed for Places API).
- Field Mask is REQUIRED in the X-Goog-FieldMask header; without it the API
  returns an error. Keeping the mask narrow controls both response size and
  cost (different SKUs are billed depending on which fields are requested).
- Text Search max pageSize is 20, max 3 pages per query -> max 60 results.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx
from loguru import logger

PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Nearby Search max radius per Google docs: 50000 meters.
NEARBY_MAX_RADIUS_M = 50000.0
# Nearby Search returns max 20 results per call, no pagination.
NEARBY_MAX_RESULT_COUNT = 20

# Retry behaviour for transient errors (429, 5xx, connection issues).
MAX_RETRIES = 3
BACKOFF_BASE_S = 1.0

# Field mask kept narrow on purpose - any addition may increase Google's
# SKU tier and cost per call.
_PLACE_FIELDS = [
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.addressComponents",
    "places.location",
    "places.websiteUri",
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
    "places.types",
    "places.primaryType",
    "places.rating",
    "places.userRatingCount",
    "places.businessStatus",
]

# Text Search supports pagination via nextPageToken; Nearby Search does not.
DEFAULT_FIELD_MASK = ",".join([*_PLACE_FIELDS, "nextPageToken"])
NEARBY_FIELD_MASK = ",".join(_PLACE_FIELDS)


@dataclass
class ParsedPlace:
    """Normalised representation of one place from a search response."""

    google_place_id: str
    name: str
    address_street: str | None = None
    address_zip: str | None = None
    address_city: str | None = None
    address_country: str | None = None
    formatted_address: str | None = None
    lat: float | None = None
    lng: float | None = None
    website: str | None = None
    phone: str | None = None
    google_categories: list[str] = field(default_factory=list)
    rating: float | None = None
    user_ratings_total: int | None = None
    business_status: str | None = None
    raw_payload: dict = field(default_factory=dict)


@dataclass
class SearchPage:
    """One page of results from Text Search."""

    places: list[ParsedPlace]
    next_page_token: str | None


def rectangle(
    *, south: float, west: float, north: float, east: float
) -> dict[str, Any]:
    """Build a locationRestriction rectangle payload for the Places API."""
    return {
        "rectangle": {
            "low": {"latitude": south, "longitude": west},
            "high": {"latitude": north, "longitude": east},
        }
    }


def circle(*, lat: float, lng: float, radius_m: float) -> dict[str, Any]:
    """Build a locationRestriction circle payload. radius_m capped at 50000."""
    return {
        "circle": {
            "center": {"latitude": lat, "longitude": lng},
            "radius": min(radius_m, NEARBY_MAX_RADIUS_M),
        }
    }


class PlacesApiError(Exception):
    """Raised when the Places API returns an error we cannot recover from."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _parse_place(payload: dict[str, Any]) -> ParsedPlace:
    """Convert one element of response['places'] into a ParsedPlace."""
    display_name = payload.get("displayName") or {}
    location = payload.get("location") or {}
    components = payload.get("addressComponents") or []

    street_number = None
    route = None
    address_zip = None
    address_city = None
    address_city_fallback = None
    address_country = None

    for comp in components:
        types = comp.get("types") or []
        short = comp.get("shortText") or comp.get("longText")
        long_text = comp.get("longText") or comp.get("shortText")
        if "street_number" in types:
            street_number = short
        elif "route" in types:
            route = long_text
        elif "postal_code" in types:
            address_zip = short
        elif "locality" in types:
            address_city = long_text
        elif "postal_town" in types:
            address_city_fallback = long_text
        elif "country" in types:
            address_country = short

    if address_city is None:
        address_city = address_city_fallback

    if route and street_number:
        address_street = f"{route} {street_number}"
    elif route:
        address_street = route
    else:
        address_street = None

    return ParsedPlace(
        google_place_id=payload.get("id", ""),
        name=(display_name.get("text") or "").strip() or "(ohne Namen)",
        address_street=address_street,
        address_zip=address_zip,
        address_city=address_city,
        address_country=address_country,
        formatted_address=payload.get("formattedAddress"),
        lat=location.get("latitude"),
        lng=location.get("longitude"),
        website=payload.get("websiteUri"),
        phone=payload.get("nationalPhoneNumber")
        or payload.get("internationalPhoneNumber"),
        google_categories=payload.get("types") or [],
        rating=payload.get("rating"),
        user_ratings_total=payload.get("userRatingCount"),
        business_status=payload.get("businessStatus"),
        raw_payload=payload,
    )


class GooglePlacesClient:
    """Minimal async client around Places API Text Search.

    The client is stateful: it owns an httpx.AsyncClient and enforces a simple
    QPS limit by sleeping between requests. Use one instance per worker run.
    """

    def __init__(
        self,
        *,
        api_key: str,
        qps: int = 10,
        field_mask: str = DEFAULT_FIELD_MASK,
        timeout: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise PlacesApiError(
                "Google Places API Key fehlt - bitte in Tenant-Config setzen"
            )
        self._api_key = api_key
        self._field_mask = field_mask
        self._min_interval = 1.0 / max(qps, 1)
        self._last_request_at = 0.0
        self._client = httpx.AsyncClient(timeout=timeout, transport=transport)

    async def __aenter__(self) -> GooglePlacesClient:
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _throttle(self) -> None:
        now = asyncio.get_event_loop().time()
        wait = self._min_interval - (now - self._last_request_at)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request_at = asyncio.get_event_loop().time()

    async def text_search(
        self,
        query: str,
        *,
        language_code: str = "de",
        region_code: str = "DE",
        page_token: str | None = None,
        page_size: int = 20,
        location_restriction: dict[str, Any] | None = None,
        location_bias: dict[str, Any] | None = None,
    ) -> SearchPage:
        """Run one Text Search request (one page of results).

        location_restriction (strict) and location_bias (soft) are mutually
        exclusive in the API; if both are passed, restriction wins.
        """
        body: dict[str, Any] = {
            "textQuery": query,
            "languageCode": language_code,
            "regionCode": region_code,
            "pageSize": page_size,
        }
        if page_token:
            body["pageToken"] = page_token
        if location_restriction:
            body["locationRestriction"] = location_restriction
        elif location_bias:
            body["locationBias"] = location_bias

        return await self._post(PLACES_TEXT_SEARCH_URL, body)

    async def nearby_search(
        self,
        *,
        center_lat: float,
        center_lng: float,
        radius_m: float,
        included_types: list[str] | None = None,
        included_primary_types: list[str] | None = None,
        excluded_types: list[str] | None = None,
        language_code: str = "de",
        region_code: str = "DE",
        max_result_count: int = NEARBY_MAX_RESULT_COUNT,
    ) -> SearchPage:
        """Run one Nearby Search (New) request.

        Unlike Text Search, Nearby Search has no pagination: at most 20 results
        per call. Saturation threshold is therefore 20, not 60.
        """
        if not (included_types or included_primary_types):
            raise PlacesApiError(
                "nearby_search requires included_types or included_primary_types"
            )

        body: dict[str, Any] = {
            "locationRestriction": circle(
                lat=center_lat, lng=center_lng, radius_m=radius_m
            ),
            "maxResultCount": min(max_result_count, NEARBY_MAX_RESULT_COUNT),
            "languageCode": language_code,
            "regionCode": region_code,
        }
        if included_types:
            body["includedTypes"] = included_types
        if included_primary_types:
            body["includedPrimaryTypes"] = included_primary_types
        if excluded_types:
            body["excludedTypes"] = excluded_types

        return await self._post(
            PLACES_NEARBY_SEARCH_URL, body, field_mask=NEARBY_FIELD_MASK
        )

    async def _post(
        self,
        url: str,
        body: dict[str, Any],
        *,
        field_mask: str | None = None,
    ) -> SearchPage:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": field_mask or self._field_mask,
        }

        last_err: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            await self._throttle()
            try:
                response = await self._client.post(url, json=body, headers=headers)
            except httpx.RequestError as e:
                last_err = e
                logger.warning(
                    "Places API request failed (attempt {n}/{max}): {err}",
                    n=attempt, max=MAX_RETRIES, err=str(e),
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_BASE_S * (2 ** (attempt - 1)))
                    continue
                raise PlacesApiError(f"Places API Verbindungsfehler: {e}") from e

            if response.status_code == 200:
                data = response.json()
                places_raw = data.get("places") or []
                return SearchPage(
                    places=[_parse_place(p) for p in places_raw],
                    next_page_token=data.get("nextPageToken"),
                )

            text = response.text[:400]
            transient = response.status_code == 429 or response.status_code >= 500
            logger.warning(
                "Places API status={status} attempt={n}/{max} body={body}",
                status=response.status_code, n=attempt, max=MAX_RETRIES, body=text,
            )
            if transient and attempt < MAX_RETRIES:
                await asyncio.sleep(BACKOFF_BASE_S * (2 ** (attempt - 1)))
                continue
            raise PlacesApiError(
                f"Places API Fehler (HTTP {response.status_code}): {text}",
                status_code=response.status_code,
            )

        # Unreachable - loop always returns or raises - but keep mypy happy.
        raise PlacesApiError(
            f"Places API Verbindungsfehler nach {MAX_RETRIES} Versuchen: {last_err}"
        )

    async def search_all_pages(
        self,
        query: str,
        *,
        language_code: str = "de",
        region_code: str = "DE",
        max_pages: int = 3,
        location_restriction: dict[str, Any] | None = None,
        location_bias: dict[str, Any] | None = None,
    ) -> list[ParsedPlace]:
        """Fetch up to max_pages pages for a single query and return all places."""
        out: list[ParsedPlace] = []
        page_token: str | None = None
        for _page_idx in range(max_pages):
            page = await self.text_search(
                query,
                language_code=language_code,
                region_code=region_code,
                page_token=page_token,
                location_restriction=location_restriction,
                location_bias=location_bias,
            )
            out.extend(page.places)
            if not page.next_page_token:
                break
            page_token = page.next_page_token
        return out
