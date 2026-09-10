"""Intel module — Marketing & Competitive Intelligence.

Cross-project boundary:
- Uses Ollama on host port 11434 (shared infrastructure, systemd-managed,
  ``OLLAMA_HOST=0.0.0.0``) — explicitly multi-tenant. Optional OpenAI
  fallback (``settings.intel_openai_fallback_enabled``).
- NEVER calls qdrant:6333 (findfox-exclusive container) or
  findfox_elasticsearch (findfox-exclusive container).
- NEVER mounts ragflow chrome-linux64 — uses its own playwright/chromium.
"""

from app.intel import models  # noqa: F401  side-effect: register models
