FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies — curl for health, plus Playwright's Chromium runtime
# deps for the intel ``web_js`` adapter. Chromium itself is fetched via
# ``playwright install --with-deps chromium`` below (kept in /ms-playwright).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright bundled Chromium (intel web_js adapter). System deps are
# installed by playwright itself. NEVER mounts /projects/ragflow/chrome-linux64
# — we own this binary inside the container.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m playwright install --with-deps chromium \
    && chown -R appuser:appuser /ms-playwright

# Application code
COPY app/ ./app/
COPY alembic.ini .
COPY alembic/ ./alembic/
COPY run_intel_worker.py .

# Logs directory
RUN mkdir -p logs && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
