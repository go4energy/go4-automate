"""Autopilot daily report — aggregates autopilot actions for user review."""

from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import AssistantItem, AssistantUndoLog


class AutopilotReportService:
    """Generates daily summaries of autopilot activity."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_daily_report(self, tenant_id: str, user_id: int) -> dict:
        """Generate a daily report from the last 24h of autopilot undo logs.

        Returns a dict with report data and stores it as an AssistantItem.
        """
        since = datetime.utcnow() - timedelta(hours=24)
        logs = await self._get_autopilot_logs(tenant_id, user_id, since)

        if not logs:
            report_data = {
                "date": datetime.utcnow().strftime("%d.%m.%Y"),
                "total_processed": 0,
                "auto_executed": 0,
                "queued": 0,
                "by_rule": {},
                "by_folder": {},
            }
        else:
            report_data = self._aggregate_logs(logs)

        # Store as AssistantItem for retrieval
        item = AssistantItem(
            tenant_id=tenant_id,
            user_id=user_id,
            connection_id=logs[0].connection_id if logs else 0,
            item_type="autopilot_report",
            external_id=f"autopilot-report-{datetime.utcnow().strftime('%Y-%m-%d')}",
            title=f"Autopilot-Bericht {report_data['date']}",
            summary=self._format_report_text(report_data),
            occurred_at=datetime.utcnow(),
            status="processed",
        )

        # Check for existing report today
        existing = await self.db.execute(
            select(AssistantItem).where(
                AssistantItem.tenant_id == tenant_id,
                AssistantItem.user_id == user_id,
                AssistantItem.item_type == "autopilot_report",
                AssistantItem.external_id == item.external_id,
            )
        )
        existing_item = existing.scalar_one_or_none()
        if existing_item:
            existing_item.summary = item.summary
            existing_item.raw_metadata_json = report_data
            await self.db.flush()
            logger.debug("Autopilot report updated for {d}", d=report_data["date"])
            return report_data

        item.raw_metadata_json = report_data
        self.db.add(item)
        await self.db.flush()
        logger.info(
            "Autopilot report created: tenant={t} user={u} date={d}",
            t=tenant_id,
            u=user_id,
            d=report_data["date"],
        )
        return report_data

    async def get_report_text(self, tenant_id: str, user_id: int) -> str:
        """Get the latest autopilot report as human-readable text."""
        result = await self.db.execute(
            select(AssistantItem)
            .where(
                AssistantItem.tenant_id == tenant_id,
                AssistantItem.user_id == user_id,
                AssistantItem.item_type == "autopilot_report",
            )
            .order_by(AssistantItem.occurred_at.desc())
            .limit(1)
        )
        item = result.scalar_one_or_none()
        if not item or not item.summary:
            return "Kein Autopilot-Bericht vorhanden."
        return item.summary

    async def get_latest_report(self, tenant_id: str, user_id: int) -> dict | None:
        """Get the latest report data dict."""
        result = await self.db.execute(
            select(AssistantItem)
            .where(
                AssistantItem.tenant_id == tenant_id,
                AssistantItem.user_id == user_id,
                AssistantItem.item_type == "autopilot_report",
            )
            .order_by(AssistantItem.occurred_at.desc())
            .limit(1)
        )
        item = result.scalar_one_or_none()
        if not item:
            return None
        return {
            "date": item.title,
            "text": item.summary,
            "data": item.raw_metadata_json,
            "created_at": item.occurred_at.isoformat() if item.occurred_at else None,
        }

    # ── Internals ─────────────────────────────────────────────────

    async def _get_autopilot_logs(
        self, tenant_id: str, user_id: int, since: datetime
    ) -> list[AssistantUndoLog]:
        """Fetch undo logs with autopilot=true from the given time window."""
        result = await self.db.execute(
            select(AssistantUndoLog)
            .where(
                AssistantUndoLog.tenant_id == tenant_id,
                AssistantUndoLog.user_id == user_id,
                AssistantUndoLog.created_at >= since,
                AssistantUndoLog.metadata_json["autopilot"].as_boolean().is_(True),
            )
            .order_by(AssistantUndoLog.created_at.desc())
        )
        return list(result.scalars().all())

    def _aggregate_logs(self, logs: list[AssistantUndoLog]) -> dict:
        """Aggregate undo logs into report stats."""
        by_rule: dict[str, int] = {}
        by_folder: dict[str, int] = {}
        auto_executed = 0
        queued = 0

        for log in logs:
            meta = log.metadata_json or {}
            rule_name = meta.get("rule_name", "Unbekannt")
            by_rule[rule_name] = by_rule.get(rule_name, 0) + 1

            after = log.after_state_json or {}
            folder = after.get("folder_name", "Unbekannt")
            by_folder[folder] = by_folder.get(folder, 0) + 1

            if log.status == "executed":
                auto_executed += 1
            else:
                queued += 1

        return {
            "date": datetime.utcnow().strftime("%d.%m.%Y"),
            "total_processed": len(logs),
            "auto_executed": auto_executed,
            "queued": queued,
            "by_rule": by_rule,
            "by_folder": by_folder,
        }

    def _format_report_text(self, data: dict) -> str:
        """Format report data as human-readable German text."""
        lines = [f"Autopilot-Bericht fuer {data['date']}:", ""]

        total = data["total_processed"]
        if total == 0:
            lines.append("Keine Emails verarbeitet.")
            return "\n".join(lines)

        lines.append("Automatisch verarbeitet:")
        if data["auto_executed"]:
            folder_parts = []
            for folder, count in data.get("by_folder", {}).items():
                folder_parts.append(f"{count}x {folder}")
            folder_str = ", ".join(folder_parts) if folder_parts else ""
            lines.append(
                f"  - {data['auto_executed']} Emails verschoben ({folder_str})"
            )
        if data["queued"]:
            lines.append(f"  - {data['queued']} Emails zur manuellen Pruefung")

        lines.append("")
        if data.get("by_rule"):
            lines.append("Aktive Regeln:")
            for rule_name, count in data["by_rule"].items():
                lines.append(f'  - "{rule_name}" ({count} Treffer)')

        lines.append("")
        if not data["queued"]:
            lines.append("Keine manuellen Eingriffe erforderlich.")

        return "\n".join(lines)
