"""Global debug bridge for LinkedIn worker.

Singleton that workers check at every step.
When active (WebSocket connected), steps are announced and wait for approval.
When inactive, all checkpoints are no-ops.

All messages are ALWAYS written to daily log files regardless of debug state.
"""

import asyncio
import contextlib
import os
from datetime import datetime

from loguru import logger

# Daily worker log file
_log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(_log_dir, exist_ok=True)

# Add daily rotating log file (separate from main app log)
_worker_log_id = logger.add(
    os.path.join(_log_dir, "worker_{time:YYYY-MM-DD}.log"),
    rotation="00:00",
    retention=None,  # Keep all — cleanup later
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
    filter=lambda record: record["extra"].get("worker_log"),
    level="DEBUG",
)

# Dedicated logger for worker entries
wlog = logger.bind(worker_log=True)


class DebugBridge:
    """Global debug state — connects worker steps to frontend WebSocket."""

    def __init__(self):
        self._ws = None
        self._step_event = asyncio.Event()
        self._cancelled = False
        self._active = False

    @property
    def is_active(self) -> bool:
        """Whether debug mode is currently enabled."""
        return self._active and self._ws is not None

    def connect(self, ws) -> None:
        """Activate debug mode with a WebSocket connection."""
        self._ws = ws
        self._active = True
        self._cancelled = False
        self._step_event.clear()
        wlog.info("[DEBUG] Debug-Modus aktiviert")

    def disconnect(self) -> None:
        """Deactivate debug mode."""
        self._active = False
        self._ws = None
        self._cancelled = True
        self._step_event.set()
        wlog.info("[DEBUG] Debug-Modus deaktiviert")

    async def checkpoint(
        self, step_id: str, description: str, details: str = ""
    ) -> bool:
        """Announce a step and wait for approval.

        Always logs to file. Only blocks when debug is active.

        Returns:
            True if approved (or debug inactive), False if cancelled.
        """
        # Always log to file
        detail_str = f" — {details}" if details else ""
        wlog.info("[STEP] {desc}{detail}", desc=description, detail=detail_str)

        if not self.is_active:
            return True

        self._step_event.clear()
        self._cancelled = False

        with contextlib.suppress(Exception):
            await self._ws.send_json({
                "type": "step",
                "step_id": step_id,
                "description": description,
                "details": details,
                "timestamp": datetime.utcnow().isoformat(),
            })

        await self._step_event.wait()

        if self._cancelled:
            wlog.warning("[STEP] Abgebrochen: {desc}", desc=description)
        else:
            wlog.debug("[STEP] Freigegeben: {desc}", desc=description)

        return not self._cancelled

    async def log(self, level: str, message: str) -> None:
        """Send a log message to frontend AND write to file.

        Always writes to file. Sends to WebSocket only when debug active.
        """
        # Always log to file
        log_fn = {
            "ok": wlog.info,
            "info": wlog.info,
            "warning": wlog.warning,
            "error": wlog.error,
            "debug": wlog.debug,
        }.get(level, wlog.info)
        log_fn("[{lvl}] {msg}", lvl=level.upper(), msg=message)

        if not self.is_active:
            return

        with contextlib.suppress(Exception):
            await self._ws.send_json({
                "type": "log",
                "level": level,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            })

    def approve(self) -> None:
        """Approve the current pending step."""
        self._cancelled = False
        self._step_event.set()

    def cancel(self) -> None:
        """Cancel the current step / stop the worker."""
        self._cancelled = True
        self._step_event.set()


# Global singleton
bridge = DebugBridge()
