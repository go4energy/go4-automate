"""Smoke test for pgvector roundtrip — kept callable as a script.

The full SQL operator ``<=>`` (cosine-distance) lives only on Postgres
with the ``vector`` extension. In the in-process SQLite test setup
this can't be exercised, so we provide:

1. A pytest marker that skips when live Postgres is unreachable.
2. A standalone ``__main__`` block that runs the roundtrip directly
   against ``async_session()``. Use it for CI / manual smoke:

::

    cd backend && source .venv/bin/activate
    python tests/test_intel/test_pgvector_roundtrip.py
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import text

from app.database import async_session
from app.intel.models import IntelSnapshot, IntelSource, IntelWatchTarget


async def _pg_alive() -> bool:
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.mark.anyio
async def test_pgvector_roundtrip_smoke():
    """Skips if live pgvector unreachable; otherwise full roundtrip."""
    if not await _pg_alive():
        pytest.skip("live Postgres/pgvector not reachable from test runner")
    await _roundtrip()


async def _roundtrip() -> None:
    # Cleanup
    async with async_session() as db:
        await db.execute(
            text("DELETE FROM intel_snapshot WHERE source_url = :u"),
            {"u": "https://pgv-test.local"},
        )
        await db.execute(
            text("DELETE FROM intel_source WHERE config->>'url' = :u"),
            {"u": "https://pgv-test.local"},
        )
        await db.execute(
            text("DELETE FROM intel_watch_target WHERE name = :n"),
            {"n": "pgvector-roundtrip"},
        )
        await db.commit()

    # Insert
    async with async_session() as db:
        t = IntelWatchTarget(
            tenant_id="go4energy",
            name="pgvector-roundtrip",
            kind="competitor",
            is_active=True,
        )
        db.add(t)
        await db.flush()
        s = IntelSource(
            tenant_id="go4energy",
            target_id=t.id,
            adapter="web",
            config={"url": "https://pgv-test.local"},
            fetch_interval_sec=3600,
            is_active=True,
        )
        db.add(s)
        await db.flush()
        emb_pos = [0.5] * 1024
        emb_neg = [-0.5] * 1024
        for label, emb in [("a", emb_pos), ("b", emb_pos), ("c", emb_neg)]:
            db.add(
                IntelSnapshot(
                    tenant_id="go4energy",
                    source_id=s.id,
                    content_hash=f"h_{label}",
                    text=f"text {label}",
                    parsed={},
                    embedding=emb,
                    source_url="https://pgv-test.local",
                )
            )
        await db.commit()
        sid, tid = s.id, t.id

    # Query: cosine distance ordering must put 'a'/'b' before 'c'
    async with async_session() as db:
        r = await db.execute(
            text(
                """
                SELECT content_hash, embedding <=> CAST(:probe AS vector) AS dist
                FROM intel_snapshot
                WHERE source_id = :sid
                ORDER BY dist ASC
                """
            ),
            {"probe": str(emb_pos), "sid": sid},
        )
        rows = r.all()
        assert len(rows) == 3, rows
        nearest = {rows[0][0], rows[1][0]}
        assert nearest == {"h_a", "h_b"}, nearest
        assert rows[2][0] == "h_c"
        assert float(rows[0][1]) < 1e-6

    # Cleanup
    async with async_session() as db:
        await db.execute(text("DELETE FROM intel_snapshot WHERE source_id = :sid"), {"sid": sid})
        await db.execute(text("DELETE FROM intel_source WHERE id = :sid"), {"sid": sid})
        await db.execute(text("DELETE FROM intel_watch_target WHERE id = :tid"), {"tid": tid})
        await db.commit()


if __name__ == "__main__":
    asyncio.run(_roundtrip())
    print("OK: pgvector roundtrip succeeded")
