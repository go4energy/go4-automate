"""Meta API service - Facebook and Instagram publishing."""

import httpx
from loguru import logger

from app.config import settings
from app.exceptions import ExternalServiceError


class MetaService:
    """Service for publishing to Facebook and Instagram via Meta Graph API."""

    def __init__(self) -> None:
        self.token = settings.meta_system_user_token
        self.page_id = settings.meta_page_id
        self.ig_id = settings.meta_instagram_business_id
        self.api_version = settings.meta_api_version
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def _check_config(self) -> None:
        """Validate that Meta API is configured."""
        if not self.token or not self.page_id:
            raise ExternalServiceError(
                "Meta API", "Token oder Page ID nicht konfiguriert"
            )

    async def post_to_facebook(self, message: str, link: str | None = None) -> str:
        """Publish a post to Facebook page. Returns post ID."""
        self._check_config()
        url = f"{self.base_url}/{self.page_id}/feed"
        payload: dict[str, str] = {
            "message": message,
            "access_token": self.token,
        }
        if link:
            payload["link"] = link

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(url, data=payload)
                resp.raise_for_status()
                data = resp.json()
                post_id = data.get("id", "")
                logger.info("Facebook Post veröffentlicht: {id}", id=post_id)
                return post_id
            except httpx.HTTPStatusError as e:
                detail = e.response.text if e.response else str(e)
                logger.error("Facebook API Fehler: {err}", err=detail)
                raise ExternalServiceError("Facebook", detail) from e
            except httpx.RequestError as e:
                logger.error("Facebook Verbindungsfehler: {err}", err=str(e))
                raise ExternalServiceError("Facebook", str(e)) from e

    async def post_to_instagram(self, caption: str, image_url: str) -> str:
        """Publish a post to Instagram (two-step: container + publish). Returns media ID."""
        self._check_config()
        if not self.ig_id:
            raise ExternalServiceError(
                "Instagram", "Instagram Business ID nicht konfiguriert"
            )

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                # Step 1: Create media container
                container_url = f"{self.base_url}/{self.ig_id}/media"
                container_resp = await client.post(
                    container_url,
                    data={
                        "image_url": image_url,
                        "caption": caption,
                        "access_token": self.token,
                    },
                )
                container_resp.raise_for_status()
                container_id = container_resp.json().get("id")

                # Step 2: Publish container
                publish_url = f"{self.base_url}/{self.ig_id}/media_publish"
                publish_resp = await client.post(
                    publish_url,
                    data={
                        "creation_id": container_id,
                        "access_token": self.token,
                    },
                )
                publish_resp.raise_for_status()
                media_id = publish_resp.json().get("id", "")
                logger.info("Instagram Post veröffentlicht: {id}", id=media_id)
                return media_id
            except httpx.HTTPStatusError as e:
                detail = e.response.text if e.response else str(e)
                logger.error("Instagram API Fehler: {err}", err=detail)
                raise ExternalServiceError("Instagram", detail) from e
            except httpx.RequestError as e:
                logger.error("Instagram Verbindungsfehler: {err}", err=str(e))
                raise ExternalServiceError("Instagram", str(e)) from e

    async def get_post_engagement(self, post_id: str) -> dict:
        """Fetch engagement metrics for a published post."""
        self._check_config()
        url = f"{self.base_url}/{post_id}"
        fields = "likes.summary(true),comments.summary(true),shares,impressions,reach"

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    url,
                    params={
                        "fields": fields,
                        "access_token": self.token,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "reach": data.get("reach", 0),
                    "impressions": data.get("impressions", 0),
                    "engagement": (
                        data.get("likes", {}).get("summary", {}).get("total_count", 0)
                        + data.get("comments", {})
                        .get("summary", {})
                        .get("total_count", 0)
                    ),
                    "shares": data.get("shares", {}).get("count", 0),
                }
            except httpx.HTTPStatusError as e:
                detail = e.response.text if e.response else str(e)
                logger.error("Meta Engagement Fehler: {err}", err=detail)
                raise ExternalServiceError("Meta API", detail) from e
            except httpx.RequestError as e:
                logger.error("Meta Verbindungsfehler: {err}", err=str(e))
                raise ExternalServiceError("Meta API", str(e)) from e
