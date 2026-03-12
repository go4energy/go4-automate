"""LinkedIn safety service - warmup, limits, and rate management."""

from datetime import datetime, timedelta
from typing import Literal

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.linkedin.models import LinkedInAccount


class SafetyService:
    """Manages account safety, warmup, and rate limiting."""

    # Warmup schedule: day -> (connections, messages, profiles)
    WARMUP_SCHEDULE = {
        0: (3, 5, 10),    # Day 0: Very conservative
        1: (5, 8, 15),
        2: (7, 10, 20),
        3: (10, 15, 25),
        4: (12, 18, 30),
        5: (15, 22, 35),
        6: (18, 25, 40),
        7: (20, 30, 50),   # Week 1 complete
        8: (22, 35, 55),
        9: (25, 38, 60),
        10: (28, 42, 70),
        11: (30, 45, 75),
        12: (32, 48, 80),
        13: (35, 50, 90),
        14: (40, 50, 100),  # Full limits after 2 weeks
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_account(self, account_id: int, tenant_id: str) -> LinkedInAccount | None:
        """Get account by ID."""
        result = await self.db.execute(
            select(LinkedInAccount).where(
                LinkedInAccount.id == account_id,
                LinkedInAccount.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def can_perform_action(
        self,
        account: LinkedInAccount,
        action_type: Literal["connection", "message", "profile"],
    ) -> tuple[bool, str]:
        """Check if an action can be performed within safety limits.

        Returns:
            tuple: (can_perform, reason)
        """
        # Check account status
        if account.status == "suspended":
            return False, "Account ist gesperrt"
        if account.status == "rate_limited":
            return False, "Account hat das Rate-Limit erreicht"
        if account.status == "inactive":
            return False, "Account ist inaktiv"

        # Get effective limits (considering warmup)
        limits = self._get_effective_limits(account)

        # Check daily usage
        if action_type == "connection" and account.connections_sent_today >= limits["connections"]:
            return False, f"Tageslimit fuer Verbindungsanfragen erreicht ({limits['connections']})"
        if action_type == "message" and account.messages_sent_today >= limits["messages"]:
            return False, f"Tageslimit fuer Nachrichten erreicht ({limits['messages']})"
        if action_type == "profile" and account.profiles_scraped_today >= limits["profiles"]:
            return False, f"Tageslimit fuer Profile erreicht ({limits['profiles']})"

        return True, "OK"

    def _get_effective_limits(self, account: LinkedInAccount) -> dict:
        """Get effective limits considering warmup phase."""
        if not account.warmup_enabled or account.warmup_day >= 14:
            # Full limits after warmup
            return {
                "connections": account.daily_connection_limit,
                "messages": account.daily_message_limit,
                "profiles": account.daily_profile_limit,
            }

        # Use warmup schedule
        day = min(account.warmup_day, 14)
        schedule = self.WARMUP_SCHEDULE.get(day, self.WARMUP_SCHEDULE[14])

        return {
            "connections": min(schedule[0], account.daily_connection_limit),
            "messages": min(schedule[1], account.daily_message_limit),
            "profiles": min(schedule[2], account.daily_profile_limit),
        }

    async def record_action(
        self,
        account: LinkedInAccount,
        action_type: Literal["connection", "message", "profile"],
    ) -> None:
        """Record an action was performed, incrementing daily counters."""
        if action_type == "connection":
            account.connections_sent_today += 1
        elif action_type == "message":
            account.messages_sent_today += 1
        elif action_type == "profile":
            account.profiles_scraped_today += 1

        await self.db.commit()

    async def reset_daily_counters(self, tenant_id: str | None = None) -> int:
        """Reset daily counters for all accounts (run at midnight).

        Args:
            tenant_id: Optional - reset only for specific tenant

        Returns:
            Number of accounts reset
        """
        query = update(LinkedInAccount).values(
            connections_sent_today=0,
            messages_sent_today=0,
            profiles_scraped_today=0,
        )

        if tenant_id:
            query = query.where(LinkedInAccount.tenant_id == tenant_id)

        result = await self.db.execute(query)
        await self.db.commit()

        count = result.rowcount
        logger.info(f"Reset daily counters for {count} LinkedIn accounts")
        return count

    async def progress_warmup(self, tenant_id: str | None = None) -> int:
        """Progress warmup day for accounts in warmup phase.

        Should be called daily at midnight.

        Args:
            tenant_id: Optional - progress only for specific tenant

        Returns:
            Number of accounts progressed
        """
        # Find accounts in warmup
        query = select(LinkedInAccount).where(
            LinkedInAccount.warmup_enabled.is_(True),
            LinkedInAccount.warmup_day < 14,
        )

        if tenant_id:
            query = query.where(LinkedInAccount.tenant_id == tenant_id)

        result = await self.db.execute(query)
        accounts = result.scalars().all()

        count = 0
        for account in accounts:
            # Start warmup if not started
            if account.warmup_started_at is None:
                account.warmup_started_at = datetime.utcnow()

            # Progress warmup day
            account.warmup_day = min(account.warmup_day + 1, 14)
            count += 1

            # Update status if warmup just completed
            if account.warmup_day >= 14 and account.status == "warmup":
                account.status = "active"
                logger.info(f"Account {account.id} ({account.name}) completed warmup")

        await self.db.commit()
        logger.info(f"Progressed warmup for {count} LinkedIn accounts")
        return count

    async def start_warmup(self, account: LinkedInAccount) -> None:
        """Start warmup period for an account."""
        account.warmup_enabled = True
        account.warmup_day = 0
        account.warmup_started_at = datetime.utcnow()
        account.status = "warmup"
        await self.db.commit()
        logger.info(f"Started warmup for account {account.id} ({account.name})")

    async def skip_warmup(self, account: LinkedInAccount) -> None:
        """Skip warmup for experienced accounts."""
        account.warmup_enabled = False
        account.warmup_day = 14
        if account.status == "warmup":
            account.status = "active"
        await self.db.commit()
        logger.info(f"Skipped warmup for account {account.id} ({account.name})")

    async def check_rate_limit_warning(
        self,
        account: LinkedInAccount,
        action_type: str,
    ) -> tuple[bool, str | None]:
        """Check if we're approaching limits and should slow down.

        Returns:
            tuple: (should_slow_down, warning_message)
        """
        limits = self._get_effective_limits(account)

        if action_type == "connection":
            used = account.connections_sent_today
            limit = limits["connections"]
        elif action_type == "message":
            used = account.messages_sent_today
            limit = limits["messages"]
        else:
            used = account.profiles_scraped_today
            limit = limits["profiles"]

        usage_percent = (used / limit) * 100 if limit > 0 else 100

        if usage_percent >= 90:
            return True, f"{action_type.title()}-Limit fast erreicht ({used}/{limit})"
        if usage_percent >= 75:
            return True, f"Vorsicht: {usage_percent:.0f}% des {action_type.title()}-Limits verwendet"

        return False, None

    async def set_rate_limited(self, account: LinkedInAccount, duration_hours: int = 24) -> None:
        """Set account as rate-limited."""
        account.status = "rate_limited"
        account.last_error = f"Rate-limited bis {datetime.utcnow() + timedelta(hours=duration_hours)}"
        await self.db.commit()
        logger.warning(f"Account {account.id} ({account.name}) marked as rate-limited for {duration_hours}h")

    async def clear_rate_limit(self, account: LinkedInAccount) -> None:
        """Clear rate-limit status if it was temporary."""
        if account.status == "rate_limited":
            account.status = "active" if not account.warmup_enabled or account.warmup_day >= 14 else "warmup"
            account.last_error = None
            await self.db.commit()
            logger.info(f"Cleared rate-limit for account {account.id} ({account.name})")

    async def get_account_stats(self, account: LinkedInAccount) -> dict:
        """Get current account stats and limits."""
        limits = self._get_effective_limits(account)

        return {
            "account_id": account.id,
            "account_name": account.name,
            "status": account.status,
            "warmup_enabled": account.warmup_enabled,
            "warmup_day": account.warmup_day,
            "warmup_days_remaining": max(0, 14 - account.warmup_day) if account.warmup_enabled else 0,
            "limits": {
                "connections": {
                    "used": account.connections_sent_today,
                    "limit": limits["connections"],
                    "remaining": max(0, limits["connections"] - account.connections_sent_today),
                },
                "messages": {
                    "used": account.messages_sent_today,
                    "limit": limits["messages"],
                    "remaining": max(0, limits["messages"] - account.messages_sent_today),
                },
                "profiles": {
                    "used": account.profiles_scraped_today,
                    "limit": limits["profiles"],
                    "remaining": max(0, limits["profiles"] - account.profiles_scraped_today),
                },
            },
        }

    async def get_tenant_stats(self, tenant_id: str) -> dict:
        """Get stats for all accounts in a tenant."""
        result = await self.db.execute(
            select(LinkedInAccount).where(LinkedInAccount.tenant_id == tenant_id)
        )
        accounts = result.scalars().all()

        stats = {
            "total_accounts": len(accounts),
            "active_accounts": sum(1 for a in accounts if a.status == "active"),
            "warmup_accounts": sum(1 for a in accounts if a.status == "warmup"),
            "rate_limited_accounts": sum(1 for a in accounts if a.status == "rate_limited"),
            "total_connections_today": sum(a.connections_sent_today for a in accounts),
            "total_messages_today": sum(a.messages_sent_today for a in accounts),
            "total_profiles_today": sum(a.profiles_scraped_today for a in accounts),
            "accounts": [],
        }

        for account in accounts:
            stats["accounts"].append(await self.get_account_stats(account))

        return stats

    async def calculate_optimal_delay(
        self,
        account: LinkedInAccount,
        action_type: str,
        base_min_seconds: int = 30,
        base_max_seconds: int = 120,
    ) -> tuple[int, int]:
        """Calculate optimal delay range based on current usage.

        Higher usage = longer delays to avoid detection.

        Returns:
            tuple: (min_seconds, max_seconds)
        """
        limits = self._get_effective_limits(account)

        if action_type == "connection":
            used = account.connections_sent_today
            limit = limits["connections"]
        elif action_type == "message":
            used = account.messages_sent_today
            limit = limits["messages"]
        else:
            used = account.profiles_scraped_today
            limit = limits["profiles"]

        usage_percent = (used / limit) * 100 if limit > 0 else 100

        # Scale delays based on usage
        if usage_percent < 50:
            multiplier = 1.0
        elif usage_percent < 75:
            multiplier = 1.5
        elif usage_percent < 90:
            multiplier = 2.0
        else:
            multiplier = 3.0

        # Also increase delays during warmup
        if account.warmup_enabled and account.warmup_day < 7:
            multiplier *= 1.5

        min_delay = int(base_min_seconds * multiplier)
        max_delay = int(base_max_seconds * multiplier)

        return min_delay, max_delay
