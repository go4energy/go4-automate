"""LinkedIn Safety Limits - randomized values for human-like behavior."""

import json
import random
from pathlib import Path
from typing import Any

from loguru import logger

# Load limits from JSON file
_LIMITS_FILE = Path(__file__).parent / "safety_limits.json"
_limits_cache: dict | None = None


def _load_limits() -> dict:
    """Load safety limits from JSON file."""
    global _limits_cache
    if _limits_cache is None:
        with open(_LIMITS_FILE) as f:
            _limits_cache = json.load(f)
    return _limits_cache


def get_all_limits() -> dict[str, dict]:
    """
    Get all safety limits with their metadata.
    Returns dict of {key: {label, unit, min, max}}
    """
    limits = _load_limits()
    # Filter out comment fields
    return {k: v for k, v in limits.items() if not k.startswith("_")}


def get_limit(key: str) -> dict | None:
    """Get a specific limit by key."""
    limits = get_all_limits()
    return limits.get(key)


def get_randomized(key: str) -> int:
    """
    Get a randomized value for a limit.
    Returns a random integer between min and max (inclusive).
    """
    limit = get_limit(key)
    if not limit:
        logger.warning("Unknown safety limit: {key}", key=key)
        return 0

    min_val = limit["min"]
    max_val = limit["max"]
    value = random.randint(min_val, max_val)

    logger.debug(
        "Randomized {key}: {value} (range {min}-{max})",
        key=key,
        value=value,
        min=min_val,
        max=max_val,
    )
    return value


def get_randomized_float(key: str) -> float:
    """
    Get a randomized float value for a limit.
    Returns a random float between min and max.
    """
    limit = get_limit(key)
    if not limit:
        logger.warning("Unknown safety limit: {key}", key=key)
        return 0.0

    min_val = limit["min"]
    max_val = limit["max"]
    value = random.uniform(min_val, max_val)

    logger.debug(
        "Randomized {key}: {value:.2f} (range {min}-{max})",
        key=key,
        value=value,
        min=min_val,
        max=max_val,
    )
    return value


class SafetySession:
    """
    A session with randomized safety values.
    Create once at the start of a job/routine, then use the values throughout.
    """

    def __init__(self):
        """Initialize with randomized values for all limits."""
        self._values: dict[str, int] = {}
        limits = get_all_limits()

        for key, limit in limits.items():
            self._values[key] = random.randint(limit["min"], limit["max"])

        logger.info("SafetySession initialized with randomized values")

    def get(self, key: str, default: int = 0) -> int:
        """Get a value from this session."""
        return self._values.get(key, default)

    def get_scroll_speed(self) -> int:
        """Scroll speed in pixels."""
        return self.get("scroll_speed_px", 900)

    def get_typing_delay(self) -> int:
        """Typing delay in milliseconds."""
        return self.get("typing_delay_ms", 700)

    def get_profile_visits_per_hour(self) -> int:
        """Max profile visits per hour."""
        return self.get("profile_visits_per_hour", 60)

    def get_profile_visits_before_pause(self) -> int:
        """Number of profile visits before taking a pause."""
        return self.get("profile_visits_before_pause", 55)

    def get_profile_visit_pause_seconds(self) -> int:
        """Pause duration after profile visits (in seconds)."""
        return self.get("profile_visit_pause_minutes", 25) * 60

    def get_messages_before_pause(self) -> int:
        """Number of messages before taking a pause."""
        return self.get("messages_before_pause", 30)

    def get_message_pause_seconds(self) -> int:
        """Pause duration after messages (in seconds)."""
        return self.get("message_pause_minutes", 7) * 60

    def to_dict(self) -> dict[str, int]:
        """Get all session values as dict."""
        return self._values.copy()


# Convenience function for quick access
def create_session() -> SafetySession:
    """Create a new SafetySession with randomized values."""
    return SafetySession()
