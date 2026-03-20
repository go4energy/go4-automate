"""Assistant module business logic."""

import re
from datetime import UTC, datetime
from types import SimpleNamespace

from loguru import logger
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.assistant.models import (
    AssistantAction,
    AssistantCategoryRegistry,
    AssistantConversation,
    AssistantConversationTurn,
    AssistantDecision,
    AssistantDraft,
    AssistantFeedback,
    AssistantItem,
    AssistantPendingIntent,
    AssistantProfile,
    AssistantRule,
    AssistantSource,
    AssistantTempTracking,
    AssistantUndoLog,
    IntegrationConnection,
)
from app.assistant.provider_router import (
    is_supported_voice_provider,
    require_graph_action_provider,
)
from app.assistant.time_utils import utc_now_naive
from app.config import settings
from app.exceptions import (
    AppError,
    DuplicateError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)


class AssistantService:
    """Orchestrates assistant profile, sources, and sub-services."""

    INBOX_ROOT_LABEL = "Inbox"
    DEFAULT_STATUS_FOLDER_NAMES = {
        "INBOX": INBOX_ROOT_LABEL,
        "TODO": f"{INBOX_ROOT_LABEL}/todo",
        "WARTEN": f"{INBOX_ROOT_LABEL}/warten",
        "TEMP": f"{INBOX_ROOT_LABEL}/temp",
        "ARCHIV": "Ablage",
    }
    INBOX_ALIASES = {"posteingang", "inbox"}

    DEFAULT_FIXED_CATEGORIES = (
        {"name": "Dringend", "color": "red"},
        {"name": "Finanzen", "color": "green"},
        {"name": "Personal", "color": "yellow"},
        {"name": "Kunden", "color": "blue"},
        {"name": "Lieferanten", "color": "purple"},
        {"name": "IT", "color": "orange"},
        {"name": "Rechtliches", "color": "red"},
        {"name": "Intern", "color": "gray"},
    )

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Profile ──────────────────────────────────────────────────────

    async def get_or_create_profile(
        self, tenant_id: str, user_id: int
    ) -> AssistantProfile | SimpleNamespace:
        """Return existing profile or create a default one."""
        if not await self._assistant_profile_trust_fields_available():
            return await self._get_or_create_profile_legacy(tenant_id, user_id)

        result = await self.db.execute(
            select(AssistantProfile).where(
                AssistantProfile.tenant_id == tenant_id,
                AssistantProfile.user_id == user_id,
            )
        )
        profile = result.scalar_one_or_none()
        if profile:
            return profile

        profile = AssistantProfile(
            tenant_id=tenant_id,
            user_id=user_id,
            llm_provider="anthropic",
            llm_model=settings.llm_model_content,
            autopilot_min_confidence=0.85,
            autopilot_max_rule_risk="medium",
            suggestion_min_confidence=0.70,
        )
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        logger.info("Created assistant profile for user {uid}", uid=user_id)
        return profile

    async def update_profile(
        self, tenant_id: str, user_id: int, updates: dict
    ) -> AssistantProfile | SimpleNamespace:
        """Partial-update the user's assistant profile."""
        if not await self._assistant_profile_trust_fields_available():
            return await self._update_profile_legacy(tenant_id, user_id, updates)

        profile = await self.get_or_create_profile(tenant_id, user_id)
        for key, value in updates.items():
            if value is not None and hasattr(profile, key):
                setattr(profile, key, value)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def _assistant_profile_trust_fields_available(self) -> bool:
        """Return whether the DB schema already contains trust-setting columns."""
        try:
            result = await self.db.execute(
                text(
                    """
                    SELECT COUNT(*) >= 3
                    FROM information_schema.columns
                    WHERE table_name = 'assistant_profiles'
                      AND column_name IN (
                        'autopilot_min_confidence',
                        'autopilot_max_rule_risk',
                        'suggestion_min_confidence'
                      )
                    """
                )
            )
            return bool(result.scalar())
        except Exception as exc:
            logger.warning(
                "Assistant profile schema check failed, using legacy fallback: {err}",
                err=str(exc),
            )
            return False

    async def _get_or_create_profile_legacy(
        self, tenant_id: str, user_id: int
    ) -> SimpleNamespace:
        """Fallback profile handling for databases without migration 061."""
        profile = await self._fetch_legacy_profile(tenant_id, user_id)
        if profile:
            return self._legacy_profile_payload(profile)

        await self.db.execute(
            text(
                """
                INSERT INTO assistant_profiles (
                    tenant_id,
                    user_id,
                    active,
                    briefing_enabled,
                    voice_enabled,
                    autopilot_enabled,
                    timezone,
                    llm_provider,
                    llm_model,
                    tts_provider,
                    stt_provider,
                    max_items_per_run,
                    default_reply_mode
                ) VALUES (
                    :tenant_id,
                    :user_id,
                    true,
                    true,
                    false,
                    false,
                    'Europe/Vienna',
                    'anthropic',
                    :llm_model,
                    'piper',
                    'faster-whisper',
                    30,
                    'draft'
                )
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id, "llm_model": settings.llm_model_content},
        )
        await self.db.flush()
        profile = await self._fetch_legacy_profile(tenant_id, user_id)
        logger.info("Created legacy assistant profile for user {uid}", uid=user_id)
        return self._legacy_profile_payload(profile)

    async def _update_profile_legacy(
        self, tenant_id: str, user_id: int, updates: dict
    ) -> SimpleNamespace:
        """Fallback profile update for databases without migration 061."""
        await self._get_or_create_profile_legacy(tenant_id, user_id)
        allowed_fields = {
            "active",
            "briefing_enabled",
            "voice_enabled",
            "autopilot_enabled",
            "timezone",
            "delivery_time",
            "llm_provider",
            "llm_model",
            "tts_provider",
            "tts_voice",
            "stt_provider",
            "max_items_per_run",
            "default_reply_mode",
        }
        assignments = []
        params = {"tenant_id": tenant_id, "user_id": user_id}
        for key, value in updates.items():
            if key in allowed_fields and value is not None:
                assignments.append(f"{key} = :{key}")
                params[key] = value

        if assignments:
            assignments.append("updated_at = NOW()")
            await self.db.execute(
                text(
                    f"""
                    UPDATE assistant_profiles
                    SET {", ".join(assignments)}
                    WHERE tenant_id = :tenant_id AND user_id = :user_id
                    """
                ),
                params,
            )
            await self.db.flush()

        profile = await self._fetch_legacy_profile(tenant_id, user_id)
        payload = self._legacy_profile_payload(profile)
        for key in (
            "autopilot_min_confidence",
            "autopilot_max_rule_risk",
            "suggestion_min_confidence",
        ):
            if updates.get(key) is not None:
                setattr(payload, key, updates[key])
        return payload

    async def _fetch_legacy_profile(self, tenant_id: str, user_id: int):
        """Read assistant profile without selecting trust-setting columns."""
        result = await self.db.execute(
            text(
                """
                SELECT
                    id,
                    tenant_id,
                    user_id,
                    active,
                    briefing_enabled,
                    voice_enabled,
                    autopilot_enabled,
                    timezone,
                    delivery_time,
                    llm_provider,
                    llm_model,
                    tts_provider,
                    tts_voice,
                    stt_provider,
                    max_items_per_run,
                    default_reply_mode,
                    created_at,
                    updated_at
                FROM assistant_profiles
                WHERE tenant_id = :tenant_id AND user_id = :user_id
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        return result.mappings().first()

    @staticmethod
    def _legacy_profile_payload(profile_row) -> SimpleNamespace:
        """Normalize a legacy assistant_profiles row to the current API response."""
        return SimpleNamespace(
            id=profile_row["id"],
            tenant_id=profile_row["tenant_id"],
            user_id=profile_row["user_id"],
            active=profile_row["active"],
            briefing_enabled=profile_row["briefing_enabled"],
            voice_enabled=profile_row["voice_enabled"],
            autopilot_enabled=profile_row["autopilot_enabled"],
            timezone=profile_row["timezone"],
            delivery_time=profile_row["delivery_time"],
            llm_provider=profile_row["llm_provider"],
            llm_model=profile_row["llm_model"],
            tts_provider=profile_row["tts_provider"],
            tts_voice=profile_row["tts_voice"],
            stt_provider=profile_row["stt_provider"],
            max_items_per_run=profile_row["max_items_per_run"],
            default_reply_mode=profile_row["default_reply_mode"],
            autopilot_min_confidence=0.85,
            autopilot_max_rule_risk="medium",
            suggestion_min_confidence=0.70,
            created_at=profile_row["created_at"],
            updated_at=profile_row["updated_at"],
        )

    # ── Sources ──────────────────────────────────────────────────────

    async def list_sources(self, tenant_id: str, user_id: int) -> list[dict]:
        """List all assistant sources with connection details."""
        result = await self.db.execute(
            select(AssistantSource)
            .where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
            )
            .order_by(AssistantSource.priority.desc(), AssistantSource.id)
        )
        sources = list(result.scalars().all())

        enriched = []
        for source in sources:
            conn_result = await self.db.execute(
                select(IntegrationConnection).where(
                    IntegrationConnection.id == source.connection_id,
                )
            )
            conn = conn_result.scalar_one_or_none()
            source_dict = {
                "id": source.id,
                "tenant_id": source.tenant_id,
                "user_id": source.user_id,
                "connection_id": source.connection_id,
                "briefing_enabled": source.briefing_enabled,
                "voice_enabled": source.voice_enabled,
                "reply_enabled": source.reply_enabled,
                "autopilot_enabled": source.autopilot_enabled,
                "priority": source.priority,
                "settings_json": source.settings_json,
                "created_at": source.created_at,
                "updated_at": source.updated_at,
                "connection": None,
            }
            if conn:
                source_dict["connection"] = {
                    "id": conn.id,
                    "provider": conn.provider,
                    "integration_type": conn.integration_type,
                    "connected_email": conn.connected_email,
                    "mailbox_address": conn.mailbox_address,
                    "account_label": conn.account_label,
                    "status": conn.status,
                    "last_synced_at": conn.last_synced_at,
                    "last_error": conn.last_error,
                }
            enriched.append(source_dict)
        return enriched

    async def add_source(
        self, tenant_id: str, user_id: int, data: dict
    ) -> AssistantSource:
        """Add an integration connection as assistant source."""
        connection_id = data["connection_id"]

        # Verify connection exists and belongs to tenant/user
        conn = await self.db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.id == connection_id,
                IntegrationConnection.tenant_id == tenant_id,
            )
        )
        if not conn.scalar_one_or_none():
            raise NotFoundError("IntegrationConnection", connection_id)

        # Check for duplicate
        existing = await self.db.execute(
            select(AssistantSource).where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
                AssistantSource.connection_id == connection_id,
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("AssistantSource", "connection_id")

        source = AssistantSource(tenant_id=tenant_id, user_id=user_id, **data)
        self.db.add(source)
        await self.db.flush()
        await self.db.refresh(source)
        return source

    async def update_source(
        self, tenant_id: str, user_id: int, source_id: int, updates: dict
    ) -> AssistantSource:
        """Partial-update an assistant source."""
        source = await self._get_source(tenant_id, user_id, source_id)
        for key, value in updates.items():
            if value is not None and hasattr(source, key):
                setattr(source, key, value)
        await self.db.flush()
        await self.db.refresh(source)
        return source

    async def delete_source(self, tenant_id: str, user_id: int, source_id: int) -> None:
        """Remove an assistant source."""
        source = await self._get_source(tenant_id, user_id, source_id)
        await self.db.delete(source)
        await self.db.flush()

    async def get_mailbox_policy(
        self, tenant_id: str, user_id: int, source_id: int
    ) -> dict:
        """Return cached and live mailbox policy details for one source."""
        source = await self._get_source(tenant_id, user_id, source_id)
        conn = await self._get_connection_for_source(tenant_id, source)
        access_token = await self._ensure_connection_access_token(conn)
        available_folders = await self._list_mail_folders(access_token, conn)
        settings = source.settings_json or {}
        policy = settings.get("mailbox_policy") or {}
        configured_folders = policy.get("status_folders") or {}
        inbox_root = self._detect_inbox_root_name(available_folders)
        configured_names = self._normalize_status_folder_names(
            policy.get("configured_folder_names"),
            inbox_root=inbox_root,
        )

        status_folders = self._build_status_folder_map(
            configured_folders=configured_folders,
            configured_names=configured_names,
            available_folders=available_folders,
        )

        return {
            "source_id": source.id,
            "connection_id": conn.id,
            "mailbox_address": conn.mailbox_address or conn.connected_email,
            "provider": conn.provider,
            "setup_complete": self._is_mailbox_policy_complete(status_folders),
            "status_folders": status_folders,
            "configured_folder_names": configured_names,
            "available_folders": available_folders,
        }

    async def get_mailbox_policy_by_connection(
        self, tenant_id: str, user_id: int, connection_id: int
    ) -> dict:
        """Resolve mailbox policy by assistant connection instead of source id."""
        result = await self.db.execute(
            select(AssistantSource.id).where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
                AssistantSource.connection_id == connection_id,
            )
        )
        source_id = result.scalar_one_or_none()
        if source_id is None:
            raise NotFoundError("AssistantSource(connection_id)", connection_id)
        return await self.get_mailbox_policy(tenant_id, user_id, source_id)

    async def setup_mailbox_policy(
        self,
        tenant_id: str,
        user_id: int,
        source_id: int,
        *,
        create_missing: bool = True,
        folder_names: dict[str, str] | None = None,
    ) -> dict:
        """Ensure TODO/WARTEN/TEMP/ARCHIV folders exist and cache their IDs."""
        source = await self._get_source(tenant_id, user_id, source_id)
        conn = await self._get_connection_for_source(tenant_id, source)
        access_token = await self._ensure_connection_access_token(conn)

        existing_policy = (source.settings_json or {}).get("mailbox_policy") or {}
        available_folders = await self._list_mail_folders(access_token, conn)
        inbox_root = self._detect_inbox_root_name(available_folders)
        configured_names = self._normalize_status_folder_names(
            folder_names or existing_policy.get("configured_folder_names"),
            inbox_root=inbox_root,
        )
        folder_index = {
            self._folder_lookup_key(folder.get("display_name")): folder
            for folder in available_folders
            if self._folder_lookup_key(folder.get("display_name"))
        }

        status_folders = {
            "INBOX": {
                "status": "INBOX",
                "folder_id": "inbox",
                "display_name": configured_names["INBOX"],
                "configured": True,
                "system": True,
            }
        }

        created_folders: list[dict] = []
        for status in ("TODO", "WARTEN", "TEMP", "ARCHIV"):
            display_name = configured_names[status]
            folder = folder_index.get(self._folder_lookup_key(display_name))
            if not folder and create_missing:
                folder = await self._ensure_mail_folder_path(
                    access_token, conn, display_name, folder_index
                )
                if folder:
                    created_folders.append(folder)
            status_folders[status] = {
                "status": status,
                "folder_id": folder.get("id") if folder else None,
                "display_name": display_name,
                "configured": bool(folder),
                "system": False,
            }

        settings = dict(source.settings_json or {})
        settings["mailbox_policy"] = {
            "setup_complete": self._is_mailbox_policy_complete(status_folders),
            "status_folders": status_folders,
            "configured_folder_names": configured_names,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        source.settings_json = settings
        flag_modified(source, "settings_json")
        await self.db.flush()
        await self.db.refresh(source)

        available_folders = await self._list_mail_folders(access_token, conn)
        return {
            "source_id": source.id,
            "connection_id": conn.id,
            "mailbox_address": conn.mailbox_address or conn.connected_email,
            "provider": conn.provider,
            "setup_complete": settings["mailbox_policy"]["setup_complete"],
            "status_folders": status_folders,
            "configured_folder_names": configured_names,
            "available_folders": available_folders,
            "created_folders": created_folders,
        }

    async def _get_source(
        self, tenant_id: str, user_id: int, source_id: int
    ) -> AssistantSource:
        result = await self.db.execute(
            select(AssistantSource).where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
                AssistantSource.id == source_id,
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            raise NotFoundError("AssistantSource", source_id)
        return source

    async def _get_connection_for_source(
        self, tenant_id: str, source: AssistantSource
    ) -> IntegrationConnection:
        result = await self.db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.id == source.connection_id,
                IntegrationConnection.tenant_id == tenant_id,
            )
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise NotFoundError("IntegrationConnection", source.connection_id)
        return conn

    async def _list_mail_folders(
        self, access_token: str, conn: IntegrationConnection
    ) -> list[dict]:
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient

        mailbox = conn.mailbox_address or conn.connected_email
        client = MicrosoftGraphClient(access_token)
        principal = f"users/{mailbox}" if mailbox else "me"
        data = await client.get(
            f"{principal}/mailFolders",
            params={"$select": "id,displayName", "$top": "100"},
        )
        inbox_root = self._extract_inbox_root_name(data.get("value", []))
        folders = [
            {
                "id": "inbox",
                "display_name": inbox_root,
                "well_known_name": "inbox",
            }
        ]
        folders.extend(
            await self._list_mail_folder_children(
                client,
                principal,
                "inbox",
                inbox_root,
            )
        )
        for folder in data.get("value", []):
            display_name = (folder.get("displayName") or "").strip()
            if not display_name:
                continue
            if display_name.lower() in self.INBOX_ALIASES:
                continue
            folders.append(
                {
                    "id": folder.get("id"),
                    "display_name": display_name,
                    "well_known_name": folder.get("wellKnownName"),
                }
            )
            folders.extend(
                await self._list_mail_folder_children(
                    client,
                    principal,
                    folder.get("id"),
                    display_name,
                )
            )
        return folders

    async def _list_mail_folder_children(
        self, client, principal: str, parent_folder_id: str, parent_path: str
    ) -> list[dict]:
        endpoint = f"{principal}/mailFolders/{parent_folder_id}/childFolders"
        data = await client.get(
            endpoint,
            params={"$select": "id,displayName", "$top": "100"},
        )
        folders: list[dict] = []
        for folder in data.get("value", []):
            leaf_name = (folder.get("displayName") or "").strip()
            if not leaf_name:
                continue
            path = f"{parent_path}/{leaf_name}" if parent_path else leaf_name
            folders.append(
                {
                    "id": folder.get("id"),
                    "display_name": path,
                    "well_known_name": folder.get("wellKnownName"),
                }
            )
            folders.extend(
                await self._list_mail_folder_children(
                    client,
                    principal,
                    folder.get("id"),
                    path,
                )
            )
        return folders

    async def _create_mail_folder(
        self, access_token: str, conn: IntegrationConnection, display_name: str
    ) -> dict:
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient

        mailbox = conn.mailbox_address or conn.connected_email
        client = MicrosoftGraphClient(access_token)
        principal = f"users/{mailbox}" if mailbox else "me"
        created = await self._run_provider_action(
            "Mailbox-Ordner anlegen",
            client.post(
                f"{principal}/mailFolders",
                json={"displayName": display_name},
            ),
        )
        return {
            "id": created.get("id"),
            "display_name": created.get("displayName"),
            "well_known_name": created.get("wellKnownName"),
        }

    async def _create_mail_child_folder(
        self,
        client,
        principal: str,
        parent_folder_id: str | None,
        display_name: str,
    ) -> dict:
        endpoint = (
            f"{principal}/mailFolders/{parent_folder_id}/childFolders"
            if parent_folder_id
            else f"{principal}/mailFolders"
        )
        created = await self._run_provider_action(
            "Mailbox-Ordner anlegen",
            client.post(endpoint, json={"displayName": display_name}),
        )
        return {
            "id": created.get("id"),
            "display_name": created.get("displayName"),
            "well_known_name": created.get("wellKnownName"),
        }

    async def _ensure_mail_folder_path(
        self,
        access_token: str,
        conn: IntegrationConnection,
        folder_path: str,
        folder_index: dict[str, dict],
    ) -> dict | None:
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient

        segments = self._split_folder_path(folder_path)
        if not segments:
            raise ValidationError("Ordnerpfad darf nicht leer sein")

        existing = folder_index.get(self._folder_lookup_key(folder_path))
        if existing:
            return existing

        mailbox = conn.mailbox_address or conn.connected_email
        client = MicrosoftGraphClient(access_token)
        principal = f"users/{mailbox}" if mailbox else "me"

        if segments[0].lower() in self.INBOX_ALIASES:
            current_path = self.INBOX_ROOT_LABEL
            parent_folder_id = "inbox"
            remaining_segments = segments[1:]
            if not remaining_segments:
                return {"id": "inbox", "display_name": self.INBOX_ROOT_LABEL}
        else:
            current_path = ""
            parent_folder_id = None
            remaining_segments = segments

        current_folder = None
        for segment in remaining_segments:
            current_path = f"{current_path}/{segment}" if current_path else segment
            lookup_key = self._folder_lookup_key(current_path)
            existing = folder_index.get(lookup_key)
            if existing:
                current_folder = existing
                parent_folder_id = existing.get("id")
                continue
            created = await self._create_mail_child_folder(
                client,
                principal,
                parent_folder_id,
                segment,
            )
            current_folder = {
                "id": created.get("id"),
                "display_name": current_path,
                "well_known_name": created.get("well_known_name"),
            }
            folder_index[lookup_key] = current_folder
            parent_folder_id = current_folder.get("id")
        return current_folder

    @classmethod
    def _normalize_status_folder_names(
        cls,
        folder_names: dict[str, str] | None,
        *,
        inbox_root: str | None = None,
    ) -> dict[str, str]:
        raw = {
            (status or "").upper(): (value or "").strip()
            for status, value in (folder_names or {}).items()
            if (status or "").strip() and (value or "").strip()
        }
        inbox_root_name = (
            raw.get("INBOX") or (inbox_root or "").strip() or cls.DEFAULT_STATUS_FOLDER_NAMES["INBOX"]
        )
        normalized = {
            "INBOX": inbox_root_name,
            "TODO": f"{inbox_root_name}/todo",
            "WARTEN": f"{inbox_root_name}/warten",
            "TEMP": f"{inbox_root_name}/temp",
            "ARCHIV": cls.DEFAULT_STATUS_FOLDER_NAMES["ARCHIV"],
        }
        for status in normalized:
            if raw.get(status):
                normalized[status] = raw[status]
        return normalized

    @classmethod
    def _extract_inbox_root_name(cls, folders: list[dict]) -> str:
        for folder in folders:
            display_name = (folder.get("displayName") or "").strip()
            folder_id = (folder.get("id") or "").strip().lower()
            if folder_id == "inbox" and display_name:
                return display_name
            if display_name.lower() in cls.INBOX_ALIASES:
                return display_name
        return cls.INBOX_ROOT_LABEL

    @classmethod
    def _detect_inbox_root_name(cls, available_folders: list[dict]) -> str:
        for folder in available_folders:
            display_name = (folder.get("display_name") or "").strip()
            folder_id = (folder.get("id") or "").strip().lower()
            if folder_id == "inbox" and display_name:
                return display_name
            if display_name.lower() in cls.INBOX_ALIASES:
                return display_name
        return cls.INBOX_ROOT_LABEL

    @classmethod
    def _split_folder_path(cls, folder_path: str | None) -> list[str]:
        return [segment.strip() for segment in (folder_path or "").split("/") if segment.strip()]

    @classmethod
    def _canonicalize_folder_path(cls, folder_path: str | None) -> str:
        segments = cls._split_folder_path(folder_path)
        if not segments:
            return ""
        if segments[0].lower() in cls.INBOX_ALIASES:
            segments[0] = cls.INBOX_ROOT_LABEL
        return "/".join(segments)

    @classmethod
    def _folder_lookup_key(cls, folder_path: str | None) -> str:
        return cls._canonicalize_folder_path(folder_path).lower()

    @classmethod
    def _build_status_folder_map(
        cls,
        *,
        configured_folders: dict,
        configured_names: dict[str, str],
        available_folders: list[dict],
    ) -> dict[str, dict]:
        available_by_id = {folder.get("id"): folder for folder in available_folders}
        status_folders = {
            "INBOX": {
                "status": "INBOX",
                "folder_id": "inbox",
                "display_name": configured_names["INBOX"],
                "configured": bool(available_by_id.get("inbox")),
                "system": True,
            }
        }
        for status in ("TODO", "WARTEN", "TEMP", "ARCHIV"):
            configured = configured_folders.get(status) or {}
            folder_id = configured.get("folder_id")
            live_folder = available_by_id.get(folder_id)
            status_folders[status] = {
                "status": status,
                "folder_id": folder_id,
                "display_name": configured_names[status],
                "configured": bool(folder_id and live_folder),
                "system": False,
            }
        return status_folders

    @staticmethod
    def _is_mailbox_policy_complete(status_folders: dict[str, dict]) -> bool:
        return all(
            status_folders.get(status, {}).get("configured")
            for status in ("INBOX", "TODO", "WARTEN", "TEMP", "ARCHIV")
        )

    # ── Category Registry ───────────────────────────────────────────

    async def list_categories(
        self, tenant_id: str, user_id: int, include_inactive: bool = False
    ) -> list[AssistantCategoryRegistry]:
        """List tenant categories after seeding fixed defaults."""
        if not await self._assistant_table_exists("assistant_category_registry"):
            logger.warning(
                "Assistant categories table missing, returning empty list for tenant {tenant}",
                tenant=tenant_id,
            )
            return []
        await self._ensure_default_categories(tenant_id, user_id)
        query = select(AssistantCategoryRegistry).where(
            AssistantCategoryRegistry.tenant_id == tenant_id
        )
        if not include_inactive:
            query = query.where(AssistantCategoryRegistry.active.is_(True))
        query = query.order_by(
            AssistantCategoryRegistry.category_type,
            AssistantCategoryRegistry.system_default.desc(),
            AssistantCategoryRegistry.name,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _assistant_table_exists(self, table_name: str) -> bool:
        """Return whether a table exists in the current schema."""
        try:
            result = await self.db.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = current_schema()
                          AND table_name = :table_name
                    )
                    """
                ),
                {"table_name": table_name},
            )
            return bool(result.scalar())
        except Exception as exc:
            logger.warning(
                "Assistant table existence check failed for {table}: {err}",
                table=table_name,
                err=str(exc),
            )
            return False

    async def create_category(
        self, tenant_id: str, user_id: int, data: dict
    ) -> AssistantCategoryRegistry:
        """Create a new tenant category."""
        await self._ensure_default_categories(tenant_id, user_id)
        payload = self._validate_category_payload(data)
        await self._assert_category_name_available(tenant_id, payload["name"])
        if payload["category_type"] == "project" and payload.get("active", True):
            await self._ensure_project_category_capacity(tenant_id)

        category = AssistantCategoryRegistry(
            tenant_id=tenant_id,
            user_id=user_id,
            system_default=False,
            **payload,
        )
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def update_category(
        self, tenant_id: str, user_id: int, category_id: int, updates: dict
    ) -> AssistantCategoryRegistry:
        """Update an existing tenant category."""
        category = await self._get_category(tenant_id, category_id)
        payload = self._validate_category_payload(
            {**self._category_to_dict(category), **updates}
        )
        if payload["name"] != category.name:
            await self._assert_category_name_available(
                tenant_id, payload["name"], exclude_id=category.id
            )
        if (
            payload["category_type"] == "project"
            and payload.get("active", True)
            and not category.active
        ):
            await self._ensure_project_category_capacity(
                tenant_id, exclude_id=category.id
            )

        category.name = payload["name"]
        category.color = payload.get("color")
        category.active = payload.get("active", True)
        category.metadata_json = payload.get("metadata_json")
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def delete_category(
        self, tenant_id: str, user_id: int, category_id: int
    ) -> None:
        """Delete a tenant category if it is not a seeded system default."""
        category = await self._get_category(tenant_id, category_id)
        if category.system_default:
            raise ValidationError(
                "Systemkategorien koennen nicht geloescht werden. Bitte deaktivieren oder anpassen."
            )
        await self.db.delete(category)
        await self.db.flush()

    # ── TEMP Tracking ───────────────────────────────────────────────

    async def upsert_temp_tracking(
        self,
        *,
        tenant_id: str,
        user_id: int,
        connection_id: int | None,
        message_external_id: str,
        expires_at: str | datetime,
        mailbox_address: str | None = None,
        subject: str | None = None,
        sender: str | None = None,
        thread_external_id: str | None = None,
        metadata_json: dict | None = None,
    ) -> AssistantTempTracking:
        """Create or update TEMP expiry tracking for one message."""
        normalized_expires_at = self._parse_policy_datetime(expires_at, "expires_at")
        result = await self.db.execute(
            select(AssistantTempTracking).where(
                AssistantTempTracking.tenant_id == tenant_id,
                AssistantTempTracking.connection_id == connection_id,
                AssistantTempTracking.message_external_id == message_external_id,
            )
        )
        tracking = result.scalar_one_or_none()
        if not tracking:
            tracking = AssistantTempTracking(
                tenant_id=tenant_id,
                user_id=user_id,
                connection_id=connection_id,
                message_external_id=message_external_id,
            )
            self.db.add(tracking)

        tracking.thread_external_id = thread_external_id
        tracking.mailbox_address = mailbox_address
        tracking.subject = subject
        tracking.sender = sender
        tracking.expires_at = normalized_expires_at
        tracking.resolved_at = None
        tracking.resolution_status = None
        tracking.metadata_json = metadata_json
        await self.db.flush()
        await self.db.refresh(tracking)
        return tracking

    async def resolve_temp_tracking(
        self,
        *,
        tenant_id: str,
        connection_id: int | None,
        message_external_id: str,
        resolution_status: str,
    ) -> None:
        """Mark TEMP tracking as resolved when a message leaves TEMP."""
        result = await self.db.execute(
            select(AssistantTempTracking).where(
                AssistantTempTracking.tenant_id == tenant_id,
                AssistantTempTracking.connection_id == connection_id,
                AssistantTempTracking.message_external_id == message_external_id,
                AssistantTempTracking.resolved_at.is_(None),
            )
        )
        tracking = result.scalar_one_or_none()
        if not tracking:
            return
        tracking.resolved_at = utc_now_naive()
        tracking.resolution_status = resolution_status
        await self.db.flush()

    async def review_expired_temp(
        self,
        tenant_id: str,
        user_id: int,
        *,
        mailbox: str | None = None,
        limit: int = 20,
    ) -> list[AssistantTempTracking]:
        """Return unresolved TEMP items whose expiry has passed."""
        query = (
            select(AssistantTempTracking)
            .where(
                AssistantTempTracking.tenant_id == tenant_id,
                AssistantTempTracking.user_id == user_id,
                AssistantTempTracking.resolved_at.is_(None),
                AssistantTempTracking.expires_at < utc_now_naive(),
            )
            .order_by(AssistantTempTracking.expires_at.asc())
            .limit(limit)
        )
        if mailbox:
            query = query.where(AssistantTempTracking.mailbox_address == mailbox)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        now = utc_now_naive()
        for item in items:
            item.last_reviewed_at = now
        if items:
            await self.db.flush()
        return items

    async def triage_batch(
        self,
        tenant_id: str,
        user_id: int,
        *,
        source_id: int | None = None,
        mailbox: str | None = None,
        limit: int = 10,
        unread_only: bool = False,
    ) -> list[dict]:
        """Return the next inbox messages for a bounded triage batch."""
        source, conn, access_token, mailbox_address = await self._resolve_mailbox_scope(
            tenant_id=tenant_id,
            user_id=user_id,
            source_id=source_id,
            mailbox=mailbox,
        )
        messages = await self._list_graph_messages(
            access_token,
            conn,
            folder_id="inbox",
            limit=min(max(int(limit or 10), 1), 10),
            unread_only=unread_only,
        )
        return [
            self._mailbox_review_item_dict(
                source_id=source.id,
                connection_id=conn.id,
                mailbox_address=mailbox_address,
                status="INBOX",
                message=message,
            )
            for message in messages
        ]

    async def review_waiting(
        self,
        tenant_id: str,
        user_id: int,
        *,
        source_id: int | None = None,
        mailbox: str | None = None,
        older_than_days: int = 5,
        limit: int = 10,
    ) -> list[dict]:
        """Return older messages from the configured WARTEN folder."""
        return await self._review_status_folder(
            tenant_id=tenant_id,
            user_id=user_id,
            source_id=source_id,
            mailbox=mailbox,
            status="WARTEN",
            older_than_days=older_than_days,
            limit=limit,
        )

    async def review_stale_todos(
        self,
        tenant_id: str,
        user_id: int,
        *,
        source_id: int | None = None,
        mailbox: str | None = None,
        older_than_days: int = 7,
        limit: int = 10,
    ) -> list[dict]:
        """Return older messages from the configured TODO folder."""
        return await self._review_status_folder(
            tenant_id=tenant_id,
            user_id=user_id,
            source_id=source_id,
            mailbox=mailbox,
            status="TODO",
            older_than_days=older_than_days,
            limit=limit,
        )

    async def _review_status_folder(
        self,
        *,
        tenant_id: str,
        user_id: int,
        source_id: int | None,
        mailbox: str | None,
        status: str,
        older_than_days: int,
        limit: int,
    ) -> list[dict]:
        source, conn, access_token, mailbox_address = await self._resolve_mailbox_scope(
            tenant_id=tenant_id,
            user_id=user_id,
            source_id=source_id,
            mailbox=mailbox,
        )
        policy = await self.get_mailbox_policy(tenant_id, user_id, source.id)
        folder = (policy.get("status_folders") or {}).get(status) or {}
        folder_id = folder.get("folder_id")
        if not folder_id:
            raise ValidationError(
                f"Mailbox-Policy fuer Status '{status}' ist nicht eingerichtet"
            )

        messages = await self._list_graph_messages(
            access_token,
            conn,
            folder_id=folder_id,
            limit=min(max(int(limit or 10), 1), 10),
            unread_only=False,
        )
        cutoff = utc_now_naive().timestamp() - (max(int(older_than_days or 1), 1) * 86400)
        stale_messages = []
        for message in messages:
            received_at = message.get("received_at")
            if received_at and received_at.timestamp() > cutoff:
                continue
            stale_messages.append(
                self._mailbox_review_item_dict(
                    source_id=source.id,
                    connection_id=conn.id,
                    mailbox_address=mailbox_address,
                    status=status,
                    message=message,
                )
            )
        return stale_messages

    # ── Items ────────────────────────────────────────────────────────

    async def list_items(
        self,
        tenant_id: str,
        user_id: int,
        status: str | None = None,
        item_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AssistantItem]:
        """List assistant items with optional filters."""
        query = (
            select(AssistantItem)
            .where(
                AssistantItem.tenant_id == tenant_id,
                AssistantItem.user_id == user_id,
            )
            .order_by(AssistantItem.occurred_at.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        if status:
            query = query.where(AssistantItem.status == status)
        if item_type:
            query = query.where(AssistantItem.item_type == item_type)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_item(
        self, tenant_id: str, user_id: int, item_id: int
    ) -> AssistantItem:
        """Get a single item."""
        result = await self.db.execute(
            select(AssistantItem).where(
                AssistantItem.tenant_id == tenant_id,
                AssistantItem.user_id == user_id,
                AssistantItem.id == item_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("AssistantItem", item_id)
        return item

    async def _get_category(
        self, tenant_id: str, category_id: int
    ) -> AssistantCategoryRegistry:
        result = await self.db.execute(
            select(AssistantCategoryRegistry).where(
                AssistantCategoryRegistry.tenant_id == tenant_id,
                AssistantCategoryRegistry.id == category_id,
            )
        )
        category = result.scalar_one_or_none()
        if not category:
            raise NotFoundError("AssistantCategoryRegistry", category_id)
        return category

    async def _ensure_default_categories(self, tenant_id: str, user_id: int) -> None:
        result = await self.db.execute(
            select(AssistantCategoryRegistry.name).where(
                AssistantCategoryRegistry.tenant_id == tenant_id,
                AssistantCategoryRegistry.system_default.is_(True),
                AssistantCategoryRegistry.category_type == "fixed",
            )
        )
        existing = set(result.scalars().all())
        for default in self.DEFAULT_FIXED_CATEGORIES:
            if default["name"] in existing:
                continue
            self.db.add(
                AssistantCategoryRegistry(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    name=default["name"],
                    category_type="fixed",
                    color=default["color"],
                    active=True,
                    system_default=True,
                )
            )
        await self.db.flush()

    async def _assert_category_name_available(
        self, tenant_id: str, name: str, exclude_id: int | None = None
    ) -> None:
        query = select(AssistantCategoryRegistry.id).where(
            AssistantCategoryRegistry.tenant_id == tenant_id,
            func.lower(AssistantCategoryRegistry.name) == name.lower(),
        )
        if exclude_id is not None:
            query = query.where(AssistantCategoryRegistry.id != exclude_id)
        result = await self.db.execute(query)
        if result.scalar_one_or_none() is not None:
            raise DuplicateError("AssistantCategoryRegistry", "name")

    async def _resolve_mailbox_scope(
        self,
        *,
        tenant_id: str,
        user_id: int,
        source_id: int | None = None,
        mailbox: str | None = None,
    ) -> tuple[AssistantSource, IntegrationConnection, str, str | None]:
        if source_id is not None:
            source = await self._get_source(tenant_id, user_id, source_id)
        else:
            query = (
                select(AssistantSource)
                .where(
                    AssistantSource.tenant_id == tenant_id,
                    AssistantSource.user_id == user_id,
                )
                .order_by(AssistantSource.priority.desc(), AssistantSource.id.asc())
            )
            result = await self.db.execute(query)
            candidates = list(result.scalars().all())
            source = None
            for candidate in candidates:
                conn = await self._get_connection_for_source(tenant_id, candidate)
                mailbox_address = conn.mailbox_address or conn.connected_email
                if mailbox and mailbox_address != mailbox:
                    continue
                if not is_supported_voice_provider(conn.provider):
                    continue
                source = candidate
                break
            if source is None:
                raise ValidationError("Keine passende Assistant-Quelle fuer dieses Postfach gefunden")

        conn = await self._get_connection_for_source(tenant_id, source)
        require_graph_action_provider(conn.provider, "Mailbox-Review")
        mailbox_address = conn.mailbox_address or conn.connected_email
        if mailbox and mailbox_address != mailbox:
            raise ValidationError("Die angeforderte Quelle passt nicht zum ausgewaehlten Postfach")
        access_token = await self._ensure_connection_access_token(conn)
        return source, conn, access_token, mailbox_address

    async def _list_graph_messages(
        self,
        access_token: str,
        conn: IntegrationConnection,
        *,
        folder_id: str,
        limit: int,
        unread_only: bool,
    ) -> list[dict]:
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient

        mailbox = conn.mailbox_address or conn.connected_email
        client = MicrosoftGraphClient(access_token)
        principal = f"users/{mailbox}" if mailbox else "me"
        params = {
            "$top": str(max(1, min(limit, 100))),
            "$orderby": "receivedDateTime desc",
            "$select": ",".join(
                [
                    "id",
                    "conversationId",
                    "subject",
                    "from",
                    "receivedDateTime",
                    "isRead",
                    "bodyPreview",
                    "hasAttachments",
                ]
            ),
        }
        if unread_only:
            params["$filter"] = "isRead eq false"
        payload = await self._run_provider_action(
            "Mailbox-Nachrichten laden",
            client.get(f"{principal}/mailFolders/{folder_id}/messages", params=params),
        )
        messages = []
        for item in payload.get("value", []):
            sender = (item.get("from") or {}).get("emailAddress") or {}
            received_at = item.get("receivedDateTime")
            messages.append(
                {
                    "message_id": item.get("id"),
                    "thread_id": item.get("conversationId"),
                    "subject": item.get("subject") or "(kein Betreff)",
                    "sender": sender.get("address"),
                    "received_at": (
                        datetime.fromisoformat(received_at.replace("Z", "+00:00"))
                        if received_at
                        else None
                    ),
                    "snippet": item.get("bodyPreview"),
                    "is_unread": not bool(item.get("isRead", False)),
                    "has_attachments": bool(item.get("hasAttachments", False)),
                }
            )
        return messages

    @staticmethod
    def _mailbox_review_item_dict(
        *,
        source_id: int,
        connection_id: int,
        mailbox_address: str | None,
        status: str,
        message: dict,
    ) -> dict:
        return {
            "source_id": source_id,
            "connection_id": connection_id,
            "mailbox_address": mailbox_address,
            "status": status,
            "message_id": message.get("message_id"),
            "thread_id": message.get("thread_id"),
            "subject": message.get("subject") or "(kein Betreff)",
            "sender": message.get("sender"),
            "received_at": message.get("received_at"),
            "snippet": message.get("snippet"),
            "is_unread": bool(message.get("is_unread", False)),
            "has_attachments": bool(message.get("has_attachments", False)),
        }

    async def _ensure_project_category_capacity(
        self, tenant_id: str, exclude_id: int | None = None
    ) -> None:
        query = select(func.count(AssistantCategoryRegistry.id)).where(
            AssistantCategoryRegistry.tenant_id == tenant_id,
            AssistantCategoryRegistry.category_type == "project",
            AssistantCategoryRegistry.active.is_(True),
        )
        if exclude_id is not None:
            query = query.where(AssistantCategoryRegistry.id != exclude_id)
        result = await self.db.execute(query)
        if result.scalar_one() >= 15:
            raise ValidationError(
                "Maximal 15 aktive Projekt-Kategorien sind gleichzeitig erlaubt"
            )

    def _validate_category_payload(self, data: dict) -> dict:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValidationError("Kategoriename darf nicht leer sein")
        category_type = (data.get("category_type") or "fixed").strip().lower()
        if category_type not in {"fixed", "project"}:
            raise ValidationError("category_type muss 'fixed' oder 'project' sein")
        if category_type == "project" and not name.startswith("Projekt: "):
            name = f"Projekt: {name}"
        return {
            "name": name,
            "category_type": category_type,
            "color": data.get("color") or None,
            "active": data.get("active", True),
            "metadata_json": data.get("metadata_json"),
        }

    @staticmethod
    def _category_to_dict(category: AssistantCategoryRegistry) -> dict:
        return {
            "name": category.name,
            "category_type": category.category_type,
            "color": category.color,
            "active": category.active,
            "metadata_json": category.metadata_json,
        }

    @staticmethod
    def _parse_policy_datetime(value: str | datetime, field_name: str) -> datetime:
        if isinstance(value, datetime):
            return value.replace(tzinfo=None)
        raw = (value or "").strip()
        if not raw:
            raise ValidationError(f"{field_name} ist erforderlich")
        try:
            if "T" not in raw:
                return datetime.fromisoformat(f"{raw}T23:59:59")
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo:
                return parsed.astimezone(UTC).replace(tzinfo=None)
            return parsed
        except ValueError as exc:
            raise ValidationError(
                f"{field_name} muss ein gueltiges ISO-Datum oder ISO-Zeitstempel sein"
            ) from exc

    # ── Rules ────────────────────────────────────────────────────────

    async def list_rules(self, tenant_id: str, user_id: int) -> list[AssistantRule]:
        """List all rules for a user."""
        result = await self.db.execute(
            select(AssistantRule)
            .where(
                AssistantRule.tenant_id == tenant_id,
                AssistantRule.user_id == user_id,
            )
            .order_by(AssistantRule.priority.desc(), AssistantRule.id)
        )
        return list(result.scalars().all())

    async def create_rule(
        self, tenant_id: str, user_id: int, data: dict
    ) -> AssistantRule:
        """Create a new triage rule."""
        allowed_risk = {"low", "medium", "high"}
        if data.get("risk_level", "low") not in allowed_risk:
            raise ValidationError(f"risk_level muss eines von {allowed_risk} sein")

        rule = AssistantRule(tenant_id=tenant_id, user_id=user_id, **data)
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        logger.info("Created rule '{name}' for user {uid}", name=rule.name, uid=user_id)
        return rule

    async def update_rule(
        self, tenant_id: str, user_id: int, rule_id: int, updates: dict
    ) -> AssistantRule:
        """Partial-update a rule."""
        result = await self.db.execute(
            select(AssistantRule).where(
                AssistantRule.tenant_id == tenant_id,
                AssistantRule.user_id == user_id,
                AssistantRule.id == rule_id,
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise NotFoundError("AssistantRule", rule_id)

        for key, value in updates.items():
            if value is not None and hasattr(rule, key):
                setattr(rule, key, value)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def delete_rule(self, tenant_id: str, user_id: int, rule_id: int) -> None:
        """Delete a rule."""
        result = await self.db.execute(
            select(AssistantRule).where(
                AssistantRule.tenant_id == tenant_id,
                AssistantRule.user_id == user_id,
                AssistantRule.id == rule_id,
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise NotFoundError("AssistantRule", rule_id)
        await self.db.delete(rule)
        await self.db.flush()

    # ── Actions ──────────────────────────────────────────────────────

    async def list_pending_actions(
        self, tenant_id: str, user_id: int
    ) -> list[AssistantAction]:
        """List actions awaiting user approval (suggested only, not queued)."""
        result = await self.db.execute(
            select(AssistantAction)
            .where(
                AssistantAction.tenant_id == tenant_id,
                AssistantAction.user_id == user_id,
                AssistantAction.status == "suggested",
            )
            .order_by(AssistantAction.created_at.desc())
        )
        return list(result.scalars().all())

    async def approve_action(
        self, tenant_id: str, user_id: int, action_id: int
    ) -> AssistantAction:
        """Approve a pending action."""
        result = await self.db.execute(
            select(AssistantAction).where(
                AssistantAction.tenant_id == tenant_id,
                AssistantAction.user_id == user_id,
                AssistantAction.id == action_id,
            )
        )
        action = result.scalar_one_or_none()
        if not action:
            raise NotFoundError("AssistantAction", action_id)
        if action.status != "suggested":
            raise ValidationError(
                f"Aktion hat Status '{action.status}', kann nicht freigegeben werden"
            )
        action.status = "queued"
        await self.db.flush()
        await self.db.refresh(action)
        return action

    async def reject_action(
        self, tenant_id: str, user_id: int, action_id: int
    ) -> AssistantAction:
        """Reject a pending action."""
        result = await self.db.execute(
            select(AssistantAction).where(
                AssistantAction.tenant_id == tenant_id,
                AssistantAction.user_id == user_id,
                AssistantAction.id == action_id,
            )
        )
        action = result.scalar_one_or_none()
        if not action:
            raise NotFoundError("AssistantAction", action_id)
        action.status = "rejected"
        await self.db.flush()
        await self.db.refresh(action)
        return action

    # ── Drafts ───────────────────────────────────────────────────────

    async def list_drafts(
        self,
        tenant_id: str,
        user_id: int,
        *,
        status: str | None = None,
        conversation_id: int | None = None,
        limit: int = 50,
    ) -> list[AssistantDraft]:
        query = (
            select(AssistantDraft)
            .where(
                AssistantDraft.tenant_id == tenant_id,
                AssistantDraft.user_id == user_id,
            )
            .order_by(AssistantDraft.updated_at.desc(), AssistantDraft.id.desc())
            .limit(limit)
        )
        if status:
            query = query.where(AssistantDraft.status == status)
        if conversation_id:
            query = query.where(AssistantDraft.conversation_id == conversation_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_draft(
        self, tenant_id: str, user_id: int, draft_id: int
    ) -> AssistantDraft:
        result = await self.db.execute(
            select(AssistantDraft).where(
                AssistantDraft.tenant_id == tenant_id,
                AssistantDraft.user_id == user_id,
                AssistantDraft.id == draft_id,
            )
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise NotFoundError("AssistantDraft", draft_id)
        return draft

    async def update_draft(
        self, tenant_id: str, user_id: int, draft_id: int, updates: dict
    ) -> AssistantDraft:
        draft = await self.get_draft(tenant_id, user_id, draft_id)
        if draft.status != "draft":
            raise ValidationError(
                f"Entwurf hat Status '{draft.status}' und kann nicht bearbeitet werden"
            )

        recipients = updates.pop("to_recipients", None)
        for key, value in updates.items():
            if value is not None and hasattr(draft, key):
                setattr(draft, key, value)
        if recipients is not None:
            draft.to_recipients_json = {"items": recipients}
        if "body_text" in updates and updates.get("body_text") is not None:
            draft.body_html = f"<p>{draft.body_text}</p>"
        await self.db.flush()
        await self.db.refresh(draft)
        return draft

    async def send_draft(
        self, tenant_id: str, user_id: int, draft_id: int
    ) -> AssistantDraft:
        draft = await self.get_draft(tenant_id, user_id, draft_id)
        if draft.status != "draft":
            raise ValidationError(
                f"Entwurf hat Status '{draft.status}' und kann nicht gesendet werden"
            )
        conn = await self._get_connection_for_draft(draft)
        access_token = await self._ensure_connection_access_token(conn)
        mailbox = conn.mailbox_address or conn.connected_email

        require_graph_action_provider(conn.provider, "Draft-Senden")

        from app.integrations.microsoft_graph.client import MicrosoftGraphClient
        from app.integrations.microsoft_graph.mail_actions import (
            MicrosoftGraphMailActionProvider,
        )
        from app.integrations.types import MailDraft

        client = MicrosoftGraphClient(access_token)
        action_provider = MicrosoftGraphMailActionProvider(client)
        outbound = MailDraft(
            subject=draft.subject or "",
            html_body=draft.body_html or f"<p>{draft.body_text or ''}</p>",
            text_body=draft.body_text,
            to_recipients=(draft.to_recipients_json or {}).get("items", []),
        )
        if draft.draft_type == "reply" and draft.target_external_id:
            await self._run_provider_action(
                "Draft-Senden",
                action_provider.reply_to_message(
                    draft.target_external_id, outbound, mailbox=mailbox
                ),
            )
        else:
            await self._run_provider_action(
                "Draft-Senden",
                action_provider.send_mail(outbound, mailbox=mailbox),
            )

        draft.status = "sent"
        draft.sent_at = datetime.utcnow()
        await self._record_undo_log(
            tenant_id=draft.tenant_id,
            user_id=draft.user_id,
            conversation_id=draft.conversation_id,
            connection_id=draft.connection_id,
            draft_id=draft.id,
            action_type="send_draft",
            can_undo=False,
            target_ref={"draft_id": draft.id},
            before_state={"status": "draft"},
            after_state={"status": "sent"},
        )
        await self._clear_conversation_pending_reply(draft.conversation_id, draft.id)
        await self.db.flush()
        await self.db.refresh(draft)
        return draft

    async def discard_draft(
        self, tenant_id: str, user_id: int, draft_id: int
    ) -> AssistantDraft:
        draft = await self.get_draft(tenant_id, user_id, draft_id)
        if draft.status != "draft":
            raise ValidationError(
                f"Entwurf hat Status '{draft.status}' und kann nicht verworfen werden"
            )
        draft.status = "discarded"
        draft.discarded_at = datetime.utcnow()
        await self._record_undo_log(
            tenant_id=draft.tenant_id,
            user_id=draft.user_id,
            conversation_id=draft.conversation_id,
            connection_id=draft.connection_id,
            draft_id=draft.id,
            action_type="discard_draft",
            can_undo=True,
            target_ref={"draft_id": draft.id},
            before_state={"status": "draft"},
            after_state={"status": "discarded"},
        )
        await self._clear_conversation_pending_reply(draft.conversation_id, draft.id)
        await self.db.flush()
        await self.db.refresh(draft)
        return draft

    # ── Pending Intents ──────────────────────────────────────────────

    async def list_pending_intents(
        self,
        tenant_id: str,
        user_id: int,
        *,
        status: str | None = None,
        conversation_id: int | None = None,
        limit: int = 50,
    ) -> list[AssistantPendingIntent]:
        query = (
            select(AssistantPendingIntent)
            .where(
                AssistantPendingIntent.tenant_id == tenant_id,
                AssistantPendingIntent.user_id == user_id,
            )
            .order_by(
                AssistantPendingIntent.updated_at.desc(),
                AssistantPendingIntent.id.desc(),
            )
            .limit(limit)
        )
        if status:
            query = query.where(AssistantPendingIntent.status == status)
        if conversation_id:
            query = query.where(AssistantPendingIntent.conversation_id == conversation_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_pending_intent(
        self, tenant_id: str, user_id: int, intent_id: int
    ) -> AssistantPendingIntent:
        result = await self.db.execute(
            select(AssistantPendingIntent).where(
                AssistantPendingIntent.tenant_id == tenant_id,
                AssistantPendingIntent.user_id == user_id,
                AssistantPendingIntent.id == intent_id,
            )
        )
        intent = result.scalar_one_or_none()
        if not intent:
            raise NotFoundError("AssistantPendingIntent", intent_id)
        return intent

    async def cancel_pending_intent(
        self, tenant_id: str, user_id: int, intent_id: int
    ) -> AssistantPendingIntent:
        intent = await self.get_pending_intent(tenant_id, user_id, intent_id)
        if intent.status != "awaiting_confirmation":
            raise ValidationError(
                f"Intent hat Status '{intent.status}' und kann nicht abgebrochen werden"
            )
        intent.status = "cancelled"
        intent.cancelled_at = utc_now_naive()
        await self._clear_conversation_pending_intent(intent.conversation_id, intent.id)
        await self.db.flush()
        await self.db.refresh(intent)
        return intent

    async def execute_pending_intent(
        self, tenant_id: str, user_id: int, intent_id: int
    ) -> AssistantPendingIntent:
        intent = await self.get_pending_intent(tenant_id, user_id, intent_id)
        if intent.status != "awaiting_confirmation":
            raise ValidationError(
                f"Intent hat Status '{intent.status}' und kann nicht ausgefuehrt werden"
            )
        conn = await self._get_connection_for_intent(intent)
        access_token = await self._ensure_connection_access_token(conn)
        mailbox = conn.mailbox_address or conn.connected_email
        require_graph_action_provider(conn.provider, "Pending-Intents")

        from app.integrations.microsoft_graph.client import MicrosoftGraphClient
        from app.integrations.microsoft_graph.mail_actions import (
            MicrosoftGraphMailActionProvider,
        )
        from app.integrations.types import MailDraft

        client = MicrosoftGraphClient(access_token)
        action_provider = MicrosoftGraphMailActionProvider(client)
        target = intent.target_ref_json or {}
        payload = intent.payload_json or {}

        if intent.intent_type == "delete_email":
            email_id = target.get("email_id")
            if not email_id:
                raise ValidationError("delete_email Intent ohne email_id")
            await self._run_provider_action(
                "Pending-Intent delete_email",
                action_provider.move_message(
                    email_id,
                    "deleteditems",
                    mailbox=mailbox,
                ),
            )
            try:
                await self._run_provider_action(
                    "mark_read after delete_email",
                    action_provider.update_message(
                        email_id, {"isRead": True}, mailbox=mailbox
                    ),
                )
            except Exception:
                logger.warning("Could not mark email as read after delete")
            await self._record_undo_log(
                tenant_id=intent.tenant_id,
                user_id=intent.user_id,
                conversation_id=intent.conversation_id,
                connection_id=intent.connection_id,
                pending_intent_id=intent.id,
                action_type="delete_email",
                can_undo=False,
                target_ref=target,
                before_state=payload,
                after_state={"folder_name": "Gelöschte Elemente", "status": "deleted"},
            )
        elif intent.intent_type == "move_email":
            email_id = target.get("email_id")
            folder = payload.get("folder")
            if not email_id or not folder:
                raise ValidationError("move_email Intent unvollstaendig")
            folder_id = await self._resolve_folder_id(client, mailbox, folder)
            if not folder_id:
                raise ValidationError(f"Ordner '{folder}' nicht gefunden")
            await self._run_provider_action(
                "Pending-Intent move_email",
                action_provider.move_message(email_id, folder_id, mailbox=mailbox),
            )
            await self._record_undo_log(
                tenant_id=intent.tenant_id,
                user_id=intent.user_id,
                conversation_id=intent.conversation_id,
                connection_id=intent.connection_id,
                pending_intent_id=intent.id,
                action_type="move_email",
                can_undo=bool(target.get("original_folder_id")),
                target_ref=target,
                before_state={
                    "folder_id": target.get("original_folder_id"),
                    "folder_name": target.get("original_folder_name"),
                },
                after_state={"folder_id": folder_id, "folder_name": folder},
            )
        elif intent.intent_type == "move_to_status":
            email_id = target.get("email_id")
            status = payload.get("status")
            if not email_id or not status:
                raise ValidationError("move_to_status Intent unvollstaendig")
            folder_id, folder_name = await self._resolve_status_folder(
                tenant_id=intent.tenant_id,
                user_id=intent.user_id,
                connection_id=intent.connection_id,
                status=status,
            )
            await self._run_provider_action(
                "Pending-Intent move_to_status",
                action_provider.move_message(email_id, folder_id, mailbox=mailbox),
            )
            # TEMP and ARCHIV: mark as read; TODO and WARTEN: keep status
            if status in ("TEMP", "ARCHIV"):
                try:
                    await self._run_provider_action(
                        "mark_read after move_to_status",
                        action_provider.update_message(
                            email_id, {"isRead": True}, mailbox=mailbox
                        ),
                    )
                except Exception:
                    logger.warning("Could not mark email as read after move_to_status")
            await self._record_undo_log(
                tenant_id=intent.tenant_id,
                user_id=intent.user_id,
                conversation_id=intent.conversation_id,
                connection_id=intent.connection_id,
                pending_intent_id=intent.id,
                action_type="move_to_status",
                can_undo=bool(target.get("original_folder_id")),
                target_ref=target,
                before_state={
                    "folder_id": target.get("original_folder_id"),
                    "folder_name": target.get("original_folder_name"),
                    "status": target.get("original_status"),
                },
                after_state={
                    "folder_id": folder_id,
                    "folder_name": folder_name,
                    "status": status,
                },
            )
            if status == "TEMP":
                expires_at = payload.get("expires_at")
                if not expires_at:
                    raise ValidationError("TEMP erfordert ein expires_at")
                await self.upsert_temp_tracking(
                    tenant_id=intent.tenant_id,
                    user_id=intent.user_id,
                    connection_id=intent.connection_id,
                    message_external_id=email_id,
                    thread_external_id=target.get("thread_id"),
                    mailbox_address=mailbox,
                    subject=target.get("subject"),
                    sender=target.get("sender"),
                    expires_at=expires_at,
                    metadata_json={
                        "status": "TEMP",
                        "source": "move_to_status",
                    },
                )
            else:
                await self.resolve_temp_tracking(
                    tenant_id=intent.tenant_id,
                    connection_id=intent.connection_id,
                    message_external_id=email_id,
                    resolution_status=status,
                )
        elif intent.intent_type == "send_email":
            recipient = target.get("to")
            subject = target.get("subject", "")
            body = payload.get("body", "")
            if not recipient:
                raise ValidationError("send_email Intent ohne Empfaenger")
            outbound = MailDraft(
                subject=subject,
                html_body=f"<p>{body}</p>",
                text_body=body,
                to_recipients=[recipient],
            )
            await self._run_provider_action(
                "Pending-Intent send_email",
                action_provider.send_mail(outbound, mailbox=mailbox),
            )
            await self._record_undo_log(
                tenant_id=intent.tenant_id,
                user_id=intent.user_id,
                conversation_id=intent.conversation_id,
                connection_id=intent.connection_id,
                pending_intent_id=intent.id,
                action_type="send_email",
                can_undo=False,
                target_ref=target,
                before_state=payload,
                after_state={"status": "executed"},
            )
        elif intent.intent_type in {
            "accept_event",
            "decline_event",
            "tentative_event",
        }:
            event_id = target.get("event_id")
            if not event_id:
                raise ValidationError(f"{intent.intent_type} Intent ohne event_id")
            if intent.intent_type == "accept_event":
                action = "accept"
            elif intent.intent_type == "decline_event":
                action = "decline"
            else:
                action = "tentativelyAccept"
            comment = payload.get("comment", "")
            await self._run_provider_action(
                f"Pending-Intent {intent.intent_type}",
                client.post(
                    f"{'users/' + mailbox if mailbox else 'me'}/events/{event_id}/{action}",
                    json={"comment": comment, "sendResponse": True},
                ),
            )
            await self._record_undo_log(
                tenant_id=intent.tenant_id,
                user_id=intent.user_id,
                conversation_id=intent.conversation_id,
                connection_id=intent.connection_id,
                pending_intent_id=intent.id,
                action_type=intent.intent_type,
                can_undo=False,
                target_ref=target,
                before_state=payload,
                after_state={"status": "executed"},
            )
        elif intent.intent_type == "bulk_cleanup":
            operations = payload.get("operations") or []
            for op in operations:
                op_type = op.get("action")
                email_id = op.get("email_id")
                if not email_id:
                    continue
                if op_type == "move":
                    folder_id = op.get("folder_id")
                    folder_name = op.get("folder")
                    if not folder_id:
                        raise ValidationError("bulk_cleanup move ohne folder_id")
                    await self._run_provider_action(
                        "Pending-Intent bulk_cleanup_move",
                        action_provider.move_message(
                            email_id, folder_id, mailbox=mailbox
                        ),
                    )
                    await self._record_undo_log(
                        tenant_id=intent.tenant_id,
                        user_id=intent.user_id,
                        conversation_id=intent.conversation_id,
                        connection_id=intent.connection_id,
                        pending_intent_id=intent.id,
                        action_type="move_email",
                        can_undo=bool(op.get("original_folder_id")),
                        target_ref={
                            "email_id": email_id,
                            "subject": op.get("subject"),
                            "mailbox": op.get("mailbox"),
                        },
                        before_state={
                            "folder_id": op.get("original_folder_id"),
                            "folder_name": op.get("original_folder_name"),
                        },
                        after_state={"folder_id": folder_id, "folder_name": folder_name},
                        metadata={"bulk_cleanup": True},
                    )
                elif op_type == "delete":
                    await self._run_provider_action(
                        "Pending-Intent bulk_cleanup_delete",
                        action_provider.move_message(
                            email_id,
                            "deleteditems",
                            mailbox=mailbox,
                        ),
                    )
                    await self._record_undo_log(
                        tenant_id=intent.tenant_id,
                        user_id=intent.user_id,
                        conversation_id=intent.conversation_id,
                        connection_id=intent.connection_id,
                        pending_intent_id=intent.id,
                        action_type="delete_email",
                        can_undo=False,
                        target_ref={
                            "email_id": email_id,
                            "subject": op.get("subject"),
                            "mailbox": op.get("mailbox"),
                        },
                        before_state=None,
                        after_state={
                            "folder_name": "Gelöschte Elemente",
                            "status": "deleted",
                        },
                        metadata={"bulk_cleanup": True},
                    )
        else:
            raise ValidationError(
                f"Intent-Typ '{intent.intent_type}' kann noch nicht ausgefuehrt werden"
            )

        intent.status = "executed"
        intent.confirmed_at = utc_now_naive()
        intent.executed_at = utc_now_naive()
        await self._clear_conversation_pending_intent(intent.conversation_id, intent.id)
        await self.db.flush()
        await self.db.refresh(intent)
        return intent

    # ── Conversation Turns ───────────────────────────────────────────

    async def list_conversation_turns(
        self,
        tenant_id: str,
        user_id: int,
        conversation_id: int,
        *,
        limit: int = 100,
    ) -> list[AssistantConversationTurn]:
        await self._get_conversation(tenant_id, user_id, conversation_id)
        result = await self.db.execute(
            select(AssistantConversationTurn)
            .where(
                AssistantConversationTurn.tenant_id == tenant_id,
                AssistantConversationTurn.user_id == user_id,
                AssistantConversationTurn.conversation_id == conversation_id,
            )
            .order_by(AssistantConversationTurn.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Undo Logs ─────────────────────────────────────────────────────

    async def list_undo_logs(
        self,
        tenant_id: str,
        user_id: int,
        *,
        limit: int = 50,
        undoable_only: bool = False,
    ) -> list[AssistantUndoLog]:
        query = (
            select(AssistantUndoLog)
            .where(
                AssistantUndoLog.tenant_id == tenant_id,
                AssistantUndoLog.user_id == user_id,
            )
            .order_by(AssistantUndoLog.created_at.desc(), AssistantUndoLog.id.desc())
            .limit(limit)
        )
        if undoable_only:
            query = query.where(
                AssistantUndoLog.can_undo.is_(True),
                AssistantUndoLog.undone_at.is_(None),
            )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_undo_log(
        self, tenant_id: str, user_id: int, undo_log_id: int
    ) -> AssistantUndoLog:
        result = await self.db.execute(
            select(AssistantUndoLog).where(
                AssistantUndoLog.tenant_id == tenant_id,
                AssistantUndoLog.user_id == user_id,
                AssistantUndoLog.id == undo_log_id,
            )
        )
        undo_log = result.scalar_one_or_none()
        if not undo_log:
            raise NotFoundError("AssistantUndoLog", undo_log_id)
        return undo_log

    async def undo_action(
        self, tenant_id: str, user_id: int, undo_log_id: int
    ) -> AssistantUndoLog:
        undo_log = await self.get_undo_log(tenant_id, user_id, undo_log_id)
        if not undo_log.can_undo:
            raise ValidationError("Dieser Vorgang kann nicht rueckgaengig gemacht werden")
        if undo_log.undone_at:
            raise ValidationError("Dieser Vorgang wurde bereits rueckgaengig gemacht")

        if undo_log.action_type == "move_email":
            conn = await self._get_connection_for_undo_log(undo_log)
            access_token = await self._ensure_connection_access_token(conn)
            mailbox = conn.mailbox_address or conn.connected_email
            require_graph_action_provider(conn.provider, "Undo")
            email_id = (undo_log.target_ref_json or {}).get("email_id")
            folder_id = (undo_log.before_state_json or {}).get("folder_id")
            if not email_id or not folder_id:
                raise ValidationError("Undo-Information fuer move_email unvollstaendig")
            from app.integrations.microsoft_graph.client import MicrosoftGraphClient
            from app.integrations.microsoft_graph.mail_actions import (
                MicrosoftGraphMailActionProvider,
            )

            client = MicrosoftGraphClient(access_token)
            action_provider = MicrosoftGraphMailActionProvider(client)
            await action_provider.move_message(email_id, folder_id, mailbox=mailbox)
        elif undo_log.action_type == "discard_draft":
            if not undo_log.draft_id:
                raise ValidationError("Undo-Information fuer discard_draft fehlt")
            draft = await self.get_draft(tenant_id, user_id, undo_log.draft_id)
            draft.status = "draft"
            draft.discarded_at = None
        elif undo_log.action_type in {"mark_read", "mark_unread"}:
            conn = await self._get_connection_for_undo_log(undo_log)
            access_token = await self._ensure_connection_access_token(conn)
            mailbox = conn.mailbox_address or conn.connected_email
            require_graph_action_provider(conn.provider, "Undo")
            email_id = (undo_log.target_ref_json or {}).get("email_id")
            previous_is_read = (undo_log.before_state_json or {}).get("is_read")
            if email_id is None or previous_is_read is None:
                raise ValidationError("Undo-Information fuer Lesestatus unvollstaendig")
            from app.integrations.microsoft_graph.client import MicrosoftGraphClient
            from app.integrations.microsoft_graph.mail_actions import (
                MicrosoftGraphMailActionProvider,
            )

            client = MicrosoftGraphClient(access_token)
            action_provider = MicrosoftGraphMailActionProvider(client)
            await action_provider.update_message(
                email_id,
                {"isRead": previous_is_read},
                mailbox=mailbox,
            )
        elif undo_log.action_type in {"flag_email", "unflag_email"}:
            conn = await self._get_connection_for_undo_log(undo_log)
            access_token = await self._ensure_connection_access_token(conn)
            mailbox = conn.mailbox_address or conn.connected_email
            require_graph_action_provider(conn.provider, "Undo")
            email_id = (undo_log.target_ref_json or {}).get("email_id")
            previous_is_flagged = (undo_log.before_state_json or {}).get("is_flagged")
            if email_id is None or previous_is_flagged is None:
                raise ValidationError("Undo-Information fuer Markierung unvollstaendig")
            from app.integrations.microsoft_graph.client import MicrosoftGraphClient
            from app.integrations.microsoft_graph.mail_actions import (
                MicrosoftGraphMailActionProvider,
            )

            client = MicrosoftGraphClient(access_token)
            action_provider = MicrosoftGraphMailActionProvider(client)
            await action_provider.update_message(
                email_id,
                {
                    "flag": {
                        "flagStatus": (
                            "flagged" if previous_is_flagged else "notFlagged"
                        )
                    }
                },
                mailbox=mailbox,
            )
        else:
            raise ValidationError(
                f"Undo fuer '{undo_log.action_type}' ist noch nicht implementiert"
            )

        undo_log.status = "undone"
        undo_log.undone_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(undo_log)
        return undo_log

    async def undo_last_cleanup_batch(
        self, tenant_id: str, user_id: int
    ) -> dict[str, int | None]:
        """Undo the most recent bulk cleanup batch where undoable actions exist."""
        result = await self.db.execute(
            select(AssistantUndoLog)
            .where(
                AssistantUndoLog.tenant_id == tenant_id,
                AssistantUndoLog.user_id == user_id,
            )
            .order_by(AssistantUndoLog.created_at.desc(), AssistantUndoLog.id.desc())
            .limit(200)
        )
        logs = list(result.scalars().all())
        batch_id = None
        for log in logs:
            meta = log.metadata_json or {}
            if meta.get("bulk_cleanup") and log.pending_intent_id:
                batch_id = log.pending_intent_id
                break

        if not batch_id:
            raise ValidationError("Kein vorheriger Cleanup-Batch gefunden")

        batch_logs = [
            log
            for log in logs
            if log.pending_intent_id == batch_id
            and (log.metadata_json or {}).get("bulk_cleanup")
        ]
        undoable_logs = [
            log for log in batch_logs if log.can_undo and log.undone_at is None
        ]
        if not undoable_logs:
            raise ValidationError(
                "Im letzten Cleanup-Batch gibt es keine rueckgaengig machbaren Aktionen"
            )

        undone = 0
        for log in sorted(undoable_logs, key=lambda item: item.id, reverse=True):
            await self.undo_action(tenant_id, user_id, log.id)
            undone += 1

        return {
            "pending_intent_id": batch_id,
            "undone_count": undone,
            "total_batch_logs": len(batch_logs),
        }

    async def record_mail_state_change(
        self,
        *,
        tenant_id: str,
        user_id: int,
        conversation_id: int | None,
        connection_id: int | None,
        action_type: str,
        email_id: str,
        subject: str | None,
        mailbox: str | None,
        before_state: dict,
        after_state: dict,
    ) -> AssistantUndoLog:
        return await self._record_undo_log(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            connection_id=connection_id,
            action_type=action_type,
            can_undo=True,
            target_ref={
                "email_id": email_id,
                "subject": subject,
                "mailbox": mailbox,
            },
            before_state=before_state,
            after_state=after_state,
        )

    # ── Feedback ─────────────────────────────────────────────────────

    async def add_feedback(
        self, tenant_id: str, user_id: int, item_id: int, data: dict
    ) -> AssistantFeedback:
        """Record user feedback on an item."""
        # Verify item exists
        await self.get_item(tenant_id, user_id, item_id)

        feedback = AssistantFeedback(
            tenant_id=tenant_id,
            user_id=user_id,
            item_id=item_id,
            **data,
        )
        self.db.add(feedback)
        await self.db.flush()
        await self.db.refresh(feedback)
        return feedback

    # ── Decisions (read) ─────────────────────────────────────────────

    async def list_decisions_for_item(
        self, tenant_id: str, user_id: int, item_id: int
    ) -> list[AssistantDecision]:
        """List all decisions for a specific item."""
        result = await self.db.execute(
            select(AssistantDecision)
            .where(
                AssistantDecision.tenant_id == tenant_id,
                AssistantDecision.user_id == user_id,
                AssistantDecision.item_id == item_id,
            )
            .order_by(AssistantDecision.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Stats ────────────────────────────────────────────────────────

    async def get_dashboard_stats(self, tenant_id: str, user_id: int) -> dict:
        """Return quick dashboard stats."""
        from sqlalchemy import func

        items_q = await self.db.execute(
            select(func.count(AssistantItem.id)).where(
                AssistantItem.tenant_id == tenant_id,
                AssistantItem.user_id == user_id,
            )
        )
        rules_q = await self.db.execute(
            select(func.count(AssistantRule.id)).where(
                AssistantRule.tenant_id == tenant_id,
                AssistantRule.user_id == user_id,
                AssistantRule.enabled.is_(True),
            )
        )
        pending_q = await self.db.execute(
            select(func.count(AssistantAction.id)).where(
                AssistantAction.tenant_id == tenant_id,
                AssistantAction.user_id == user_id,
                AssistantAction.status == "suggested",
            )
        )
        sources_q = await self.db.execute(
            select(func.count(AssistantSource.id)).where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
            )
        )

        return {
            "total_items": items_q.scalar() or 0,
            "active_rules": rules_q.scalar() or 0,
            "pending_actions": pending_q.scalar() or 0,
            "connected_sources": sources_q.scalar() or 0,
        }

    async def get_mailbox_health(
        self, tenant_id: str, user_id: int
    ) -> list[dict]:
        """Return live mailbox health snapshots for connected sources."""
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient
        from app.integrations.microsoft_graph.mail_read import (
            MicrosoftGraphMailReadProvider,
        )

        rules_result = await self.db.execute(
            select(AssistantRule).where(
                AssistantRule.tenant_id == tenant_id,
                AssistantRule.user_id == user_id,
                AssistantRule.enabled.is_(True),
            )
        )
        rules = list(rules_result.scalars().all())

        result = await self.db.execute(
            select(AssistantSource)
            .where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
            )
            .order_by(AssistantSource.priority.desc(), AssistantSource.id.asc())
        )
        sources = list(result.scalars().all())
        snapshots = []
        for source in sources:
            conn_result = await self.db.execute(
                select(IntegrationConnection).where(
                    IntegrationConnection.id == source.connection_id
                )
            )
            conn = conn_result.scalar_one_or_none()
            if not conn or not is_supported_voice_provider(conn.provider):
                continue

            access_token = await self._ensure_connection_access_token(conn)
            mailbox = conn.mailbox_address or conn.connected_email
            client = MicrosoftGraphClient(access_token)
            provider = MicrosoftGraphMailReadProvider(client)

            count_payload = await client.get(
                f"{'users/' + mailbox if mailbox else 'me'}/messages",
                params={"$top": "1", "$count": "true", "$filter": "isRead eq false"},
                headers={"ConsistencyLevel": "eventual"},
            )
            unread_count = int(count_payload.get("@odata.count", 0) or 0)

            sample = await provider.list_messages(
                mailbox=mailbox,
                unread_only=True,
                limit=30,
            )
            cleanup_candidate_count = sum(
                1 for message in sample if self._message_matches_any_rule(message, mailbox, rules)
            )
            cleanup_recommended = unread_count >= 15 or cleanup_candidate_count >= 5
            health_score = max(
                0,
                100 - min(unread_count * 2, 60) - min(cleanup_candidate_count * 5, 40),
            )
            summary = self._build_mailbox_health_summary(
                unread_count,
                cleanup_candidate_count,
                cleanup_recommended,
            )

            snapshots.append(
                {
                    "connection_id": conn.id,
                    "mailbox_address": mailbox,
                    "account_label": conn.account_label,
                    "provider": conn.provider,
                    "unread_count": unread_count,
                    "recent_sample_count": len(sample),
                    "cleanup_candidate_count": cleanup_candidate_count,
                    "cleanup_recommended": cleanup_recommended,
                    "health_score": health_score,
                    "summary": summary,
                }
            )
        return snapshots

    def _message_matches_any_rule(self, message, mailbox: str | None, rules: list[AssistantRule]) -> bool:
        title = (getattr(message, "subject", "") or "").lower()
        sender = (getattr(message, "from_email", "") or "").lower()
        snippet = (getattr(message, "snippet", "") or "").lower()
        for rule in rules:
            criteria = rule.match_criteria_json or {}
            if not criteria:
                continue
            if "sender_domain" in criteria and criteria["sender_domain"].lower() not in sender:
                continue
            if "sender_contains" in criteria and criteria["sender_contains"].lower() not in sender:
                continue
            if "subject_contains" in criteria and criteria["subject_contains"].lower() not in title:
                continue
            if "subject_regex" in criteria:
                try:
                    if not re.search(criteria["subject_regex"], getattr(message, "subject", "") or "", re.IGNORECASE):
                        continue
                except re.error:
                    continue
            if "keywords" in criteria:
                keywords = [k.lower() for k in criteria["keywords"]]
                if not any(kw in title or kw in snippet for kw in keywords):
                    continue
            if "mailbox" in criteria and (mailbox or "").lower() != criteria["mailbox"].lower():
                continue
            return True
        return False

    @staticmethod
    def _build_mailbox_health_summary(
        unread_count: int,
        cleanup_candidate_count: int,
        cleanup_recommended: bool,
    ) -> str:
        if cleanup_recommended:
            return (
                f"{unread_count} ungelesene Emails, davon {cleanup_candidate_count} "
                f"voraussichtlich direkt bereinigbar."
            )
        return f"{unread_count} ungelesene Emails, aktuell kein akuter Bereinigungsbedarf."

    async def _get_conversation(
        self, tenant_id: str, user_id: int, conversation_id: int
    ) -> AssistantConversation:
        result = await self.db.execute(
            select(AssistantConversation).where(
                AssistantConversation.tenant_id == tenant_id,
                AssistantConversation.user_id == user_id,
                AssistantConversation.id == conversation_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise NotFoundError("AssistantConversation", conversation_id)
        return conversation

    async def _get_connection_for_draft(self, draft: AssistantDraft) -> IntegrationConnection:
        if not draft.connection_id:
            raise ValidationError("Entwurf hat keine Verbindung")
        result = await self.db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.id == draft.connection_id,
                IntegrationConnection.tenant_id == draft.tenant_id,
            )
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise NotFoundError("IntegrationConnection", draft.connection_id)
        return conn

    async def _get_connection_for_intent(
        self, intent: AssistantPendingIntent
    ) -> IntegrationConnection:
        if not intent.connection_id:
            raise ValidationError("Pending-Intent hat keine Verbindung")
        result = await self.db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.id == intent.connection_id,
                IntegrationConnection.tenant_id == intent.tenant_id,
            )
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise NotFoundError("IntegrationConnection", intent.connection_id)
        return conn

    async def _get_connection_for_undo_log(
        self, undo_log: AssistantUndoLog
    ) -> IntegrationConnection:
        if not undo_log.connection_id:
            raise ValidationError("Undo-Log hat keine Verbindung")
        result = await self.db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.id == undo_log.connection_id,
                IntegrationConnection.tenant_id == undo_log.tenant_id,
            )
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise NotFoundError("IntegrationConnection", undo_log.connection_id)
        return conn

    async def _ensure_connection_access_token(self, conn: IntegrationConnection) -> str:
        from app.assistant.intake import AssistantIntakeService

        try:
            return await AssistantIntakeService(self.db)._ensure_access_token(conn)
        except AppError:
            raise
        except Exception as exc:
            logger.exception(
                "Assistant token refresh failed for connection {cid}", cid=conn.id
            )
            raise ExternalServiceError(
                "Integration-Authentifizierung",
                "Zugriffstoken konnte nicht aktualisiert werden",
            ) from exc

    async def _run_provider_action(self, label: str, awaitable):
        try:
            return await awaitable
        except AppError:
            raise
        except Exception as exc:
            logger.exception("Assistant provider action failed: {label}", label=label)
            raise ExternalServiceError(
                "Assistant-Provider",
                f"{label} fehlgeschlagen",
            ) from exc

    async def _resolve_folder_id(
        self, client, mailbox: str | None, folder_name: str
    ) -> str | None:
        principal = f"users/{mailbox}" if mailbox else "me"
        data = await client.get(
            f"{principal}/mailFolders",
            params={"$select": "id,displayName", "$top": "100"},
        )
        for folder in data.get("value", []):
            if folder.get("displayName", "").lower() == folder_name.lower():
                return folder.get("id")
        return None


    async def _resolve_status_folder(
        self,
        *,
        tenant_id: str,
        user_id: int,
        connection_id: int | None,
        status: str,
    ) -> tuple[str, str]:
        normalized_status = (status or "").upper()
        if normalized_status == "INBOX":
            return "inbox", "Posteingang"
        if normalized_status not in {"TODO", "WARTEN", "TEMP", "ARCHIV"}:
            raise ValidationError(f"Unbekannter Status '{status}'")
        if not connection_id:
            raise ValidationError("Status-Aktion ohne connection_id")

        result = await self.db.execute(
            select(AssistantSource).where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
                AssistantSource.connection_id == connection_id,
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            raise ValidationError("AssistantSource fuer Status-Aktion nicht gefunden")

        mailbox_policy = ((source.settings_json or {}).get("mailbox_policy") or {})
        folder = (mailbox_policy.get("status_folders") or {}).get(normalized_status) or {}
        folder_id = folder.get("folder_id")
        if not folder_id:
            raise ValidationError(
                f"Status-Ordner '{normalized_status}' ist fuer diese Mailbox nicht konfiguriert"
            )
        return folder_id, folder.get("display_name") or normalized_status

    async def _clear_conversation_pending_reply(
        self, conversation_id: int | None, draft_id: int
    ) -> None:
        if not conversation_id:
            return
        conversation = await self._get_conversation_by_id(conversation_id)
        if not conversation or not conversation.context_json:
            return
        pending = conversation.context_json.get("pending_reply") or {}
        if pending.get("id") == draft_id:
            conversation.context_json = {
                **conversation.context_json,
                "pending_draft_id": None,
                "pending_reply": None,
            }
            flag_modified(conversation, "context_json")

    async def _clear_conversation_pending_intent(
        self, conversation_id: int | None, intent_id: int
    ) -> None:
        if not conversation_id:
            return
        conversation = await self._get_conversation_by_id(conversation_id)
        if not conversation or not conversation.context_json:
            return
        pending = conversation.context_json.get("pending_confirmation") or {}
        if pending.get("id") == intent_id:
            conversation.context_json = {
                **conversation.context_json,
                "pending_intent_id": None,
                "pending_confirmation": None,
            }
            flag_modified(conversation, "context_json")

    async def _get_conversation_by_id(
        self, conversation_id: int
    ) -> AssistantConversation | None:
        result = await self.db.execute(
            select(AssistantConversation).where(
                AssistantConversation.id == conversation_id
            )
        )
        return result.scalar_one_or_none()

    async def _record_undo_log(
        self,
        *,
        tenant_id: str,
        user_id: int,
        conversation_id: int | None,
        connection_id: int | None,
        action_type: str,
        can_undo: bool,
        target_ref: dict | None = None,
        before_state: dict | None = None,
        after_state: dict | None = None,
        metadata: dict | None = None,
        draft_id: int | None = None,
        pending_intent_id: int | None = None,
    ) -> AssistantUndoLog:
        undo_log = AssistantUndoLog(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            connection_id=connection_id,
            draft_id=draft_id,
            pending_intent_id=pending_intent_id,
            action_type=action_type,
            status="executed",
            can_undo=can_undo,
            target_ref_json=target_ref,
            before_state_json=before_state,
            after_state_json=after_state,
            metadata_json=metadata,
        )
        self.db.add(undo_log)
        await self.db.flush()
        return undo_log

    # ── Connection + Source ─────────────────────────────────────────

    async def create_connection_and_source(
        self,
        tenant_id: str,
        user_id: int,
        provider: str,
        connected_email: str,
        encrypted_token: str,
        mailbox_address: str | None = None,
        scope: str = "personal",
    ) -> tuple[IntegrationConnection, AssistantSource]:
        """Create an IntegrationConnection and link it as AssistantSource."""
        from app.assistant.models import IntegrationConnectionCapability

        effective_mailbox = mailbox_address or connected_email
        label = effective_mailbox

        # Upsert connection (match on all unique constraint columns)
        existing = await self.db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.tenant_id == tenant_id,
                IntegrationConnection.user_id == user_id,
                IntegrationConnection.provider == provider,
                IntegrationConnection.integration_type == "email",
                IntegrationConnection.mailbox_address == effective_mailbox,
            )
        )
        conn = existing.scalar_one_or_none()
        if conn:
            conn.encrypted_token = encrypted_token
            conn.status = "connected"
            conn.last_error = None
        else:
            conn = IntegrationConnection(
                tenant_id=tenant_id,
                user_id=user_id,
                provider=provider,
                integration_type="email",
                auth_mode="delegated",
                connected_email=connected_email,
                mailbox_address=effective_mailbox,
                account_label=label,
                encrypted_token=encrypted_token,
                status="connected",
                metadata_json={"scope": scope},
            )
            self.db.add(conn)
            await self.db.flush()

            # Grant capabilities
            for cap in ("read_mail", "read_calendar", "send_mail", "mail_actions"):
                self.db.add(
                    IntegrationConnectionCapability(
                        connection_id=conn.id,
                        capability=cap,
                        granted=True,
                    )
                )

        await self.db.flush()
        await self.db.refresh(conn)

        # Ensure source exists
        source_result = await self.db.execute(
            select(AssistantSource).where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
                AssistantSource.connection_id == conn.id,
            )
        )
        source = source_result.scalar_one_or_none()
        if not source:
            source = AssistantSource(
                tenant_id=tenant_id,
                user_id=user_id,
                connection_id=conn.id,
                briefing_enabled=True,
            )
            self.db.add(source)
            await self.db.flush()
            await self.db.refresh(source)

        return conn, source

    # ── Briefing ─────────────────────────────────────────────────────

    async def run_briefing(
        self,
        tenant_id: str,
        user_id: int,
        max_items: int = 30,
    ) -> dict:
        """Run a briefing: intake → classify → rules → generate text."""
        from datetime import datetime

        from app.assistant.classifier import AssistantClassifier
        from app.assistant.intake import AssistantIntakeService
        from app.assistant.rules import AssistantRuleEngine

        # 1. Intake
        intake = AssistantIntakeService(self.db)
        intake_result = await intake.run_intake(tenant_id, user_id)
        logger.info("Intake: {r}", r=intake_result)

        # 2. Get recent unclassified items
        items = await self.list_items(tenant_id, user_id, status="new", limit=max_items)

        # 3. Classify
        classifier = AssistantClassifier(self.db)
        decisions = await classifier.classify_items(tenant_id, user_id, items)

        # 4. Apply rules
        rule_engine = AssistantRuleEngine(self.db)
        actions = await rule_engine.apply_rules(tenant_id, user_id, items)

        # 5. Build briefing text
        briefing_text = self._build_briefing_text(items, decisions)

        await self.db.flush()

        return {
            "items_processed": len(items),
            "briefing_text": briefing_text,
            "audio_url": None,
            "generated_at": datetime.now(UTC).isoformat(),
            "actions_created": len(actions),
        }

    @staticmethod
    def _build_briefing_text(
        items: list[AssistantItem],
        decisions: list[AssistantDecision],
    ) -> str:
        """Build a simple text briefing from classified items."""
        if not items:
            return "Keine neuen Nachrichten oder Termine."

        # Map item_id -> importance
        importance_map: dict[int, str] = {}
        for d in decisions:
            if d.decision_type == "importance":
                importance_map[d.item_id] = d.decision_value or "medium"

        lines = []
        high_items = [i for i in items if importance_map.get(i.id) == "high"]
        medium_items = [i for i in items if importance_map.get(i.id) == "medium"]
        low_items = [i for i in items if importance_map.get(i.id) == "low"]

        if high_items:
            lines.append(f"Wichtig ({len(high_items)}):")
            for item in high_items[:10]:
                lines.append(f"  - {item.title or '(ohne Betreff)'}")
                if item.sender:
                    lines[-1] += f" (von {item.sender})"

        if medium_items:
            lines.append(f"\nInformativ ({len(medium_items)}):")
            for item in medium_items[:10]:
                lines.append(f"  - {item.title or '(ohne Betreff)'}")

        if low_items:
            lines.append(f"\nNiedrige Prioritaet ({len(low_items)}):")
            lines.append(
                f"  {len(low_items)} Nachrichten (Newsletter, Benachrichtigungen)"
            )

        return "\n".join(lines)
