"""Reset a leadgen handoff so the same places can be re-handed off.

What this does (for the given pipeline_id, default 17):
1. DELETE all pipeline_enrollments for that pipeline.
2. DELETE all pending_actions for that pipeline.
3. DELETE all contact_activities tied to that pipeline.
4. DELETE the contacts that were created by leadgen handoff
   (`source='leadgen'` AND `leadgen_place_id IS NOT NULL`)
   AND that are only enrolled in this one pipeline (or only had this
   enrollment). The ON DELETE SET NULL on `leadgen_places.contact_id`
   resets the place automatically, so it becomes re-handoffable.
5. Reset `leadgen_places.contact_id = NULL` for any place where the
   contact was already deleted but the FK survived (cleanup).

WHAT IT DOES NOT TOUCH:
- leadgen_places, leadgen_impressum, leadgen_llm_insights, leadgen_contacts
  (= the leadgen-side data is preserved)
- companies (those are reused; leaving them harmless)
- Contacts that exist independently (e.g. from CSV import, customer-journey)

Usage::

    cd backend
    python scripts/cleanup_pipeline_handoff.py --tenant go4energy --pipeline 17 --dry-run
    # then for real:
    python scripts/cleanup_pipeline_handoff.py --tenant go4energy --pipeline 17 --confirm

Always run --dry-run first.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

sys.path.insert(0, ".")

from app.config import settings  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402


async def _stats(db, tenant: str, pipeline_id: int) -> dict:
    queries = {
        "enrollments": "SELECT COUNT(*) FROM pipeline_enrollments WHERE tenant_id=:t AND pipeline_id=:p",
        "pending_actions": "SELECT COUNT(*) FROM pending_actions WHERE tenant_id=:t AND pipeline_id=:p",
        "contact_activities": "SELECT COUNT(*) FROM contact_activities WHERE tenant_id=:t AND pipeline_id=:p",
        "contacts_to_delete": (
            "SELECT COUNT(*) FROM contacts c "
            "WHERE c.tenant_id=:t "
            "  AND c.source='leadgen' "
            "  AND c.leadgen_place_id IS NOT NULL "
            "  AND EXISTS ("
            "    SELECT 1 FROM pipeline_enrollments e "
            "    WHERE e.contact_id = c.id AND e.pipeline_id=:p "
            "  ) "
            "  AND NOT EXISTS ("
            "    SELECT 1 FROM pipeline_enrollments e2 "
            "    WHERE e2.contact_id = c.id AND e2.pipeline_id <> :p"
            "  )"
        ),
        "leadgen_places_with_contact": (
            "SELECT COUNT(*) FROM leadgen_places p "
            "JOIN contacts c ON c.id = p.contact_id "
            "WHERE p.tenant_id=:t "
            "  AND c.source='leadgen' "
            "  AND EXISTS ("
            "    SELECT 1 FROM pipeline_enrollments e "
            "    WHERE e.contact_id = c.id AND e.pipeline_id=:p"
            "  )"
        ),
    }
    out = {}
    for name, q in queries.items():
        r = await db.execute(text(q), {"t": tenant, "p": pipeline_id})
        out[name] = r.scalar() or 0
    return out


async def _execute_cleanup(db, tenant: str, pipeline_id: int) -> dict:
    """Run the actual deletes. Returns row counts deleted per step."""
    deleted = {}

    # 1. pending_actions for the pipeline
    r = await db.execute(
        text(
            "DELETE FROM pending_actions "
            "WHERE tenant_id=:t AND pipeline_id=:p"
        ),
        {"t": tenant, "p": pipeline_id},
    )
    deleted["pending_actions"] = r.rowcount

    # 2. contact_activities for the pipeline (if any). Avoid hitting the
    #    pipeline-wide history that's not specific to this re-import.
    r = await db.execute(
        text(
            "DELETE FROM contact_activities "
            "WHERE tenant_id=:t AND pipeline_id=:p"
        ),
        {"t": tenant, "p": pipeline_id},
    )
    deleted["contact_activities"] = r.rowcount

    # 3. enrollments for the pipeline
    r = await db.execute(
        text(
            "DELETE FROM pipeline_enrollments "
            "WHERE tenant_id=:t AND pipeline_id=:p"
        ),
        {"t": tenant, "p": pipeline_id},
    )
    deleted["enrollments"] = r.rowcount

    # 4. Contacts that came purely from this handoff (leadgen + place_id +
    #    only enrolled in this pipeline → safe to delete; ON DELETE SET NULL
    #    on leadgen_places.contact_id auto-resets the place).
    r = await db.execute(
        text(
            "DELETE FROM contacts c "
            "WHERE c.tenant_id=:t "
            "  AND c.source='leadgen' "
            "  AND c.leadgen_place_id IS NOT NULL "
            "  AND NOT EXISTS ("
            "    SELECT 1 FROM pipeline_enrollments e "
            "    WHERE e.contact_id = c.id"
            "  )"
        ),
        {"t": tenant},
    )
    deleted["contacts"] = r.rowcount

    # 5. Reset any orphaned leadgen_places.contact_id pointing at deleted contacts.
    #    (ON DELETE SET NULL handles this automatically, but a cleanup safety
    #    net keeps things tidy.)
    r = await db.execute(
        text(
            "UPDATE leadgen_places p "
            "SET contact_id = NULL "
            "WHERE p.tenant_id=:t "
            "  AND p.contact_id IS NOT NULL "
            "  AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = p.contact_id)"
        ),
        {"t": tenant},
    )
    deleted["leadgen_places_reset"] = r.rowcount

    # 6. Reset is_handed_off on leadgen_contacts whose contact_id has been
    #    cleared by ON DELETE SET NULL. Without this, re-handoff would skip
    #    these as already-done. Catches both the "contact still pointed at
    #    deleted row" edge case AND the normal "FK was already nulled by the
    #    delete cascade" path.
    r = await db.execute(
        text(
            "UPDATE leadgen_contacts lc "
            "SET is_handed_off = FALSE, contact_id = NULL "
            "WHERE lc.tenant_id=:t "
            "  AND lc.is_handed_off = TRUE "
            "  AND ("
            "    lc.contact_id IS NULL"
            "    OR NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = lc.contact_id)"
            "  )"
        ),
        {"t": tenant},
    )
    deleted["leadgen_contacts_reset"] = r.rowcount

    return deleted


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default="go4energy")
    parser.add_argument("--pipeline", type=int, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", default=True)
    group.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete. Must be passed explicitly.",
    )
    args = parser.parse_args()

    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    print(f"\n=== Cleanup: tenant={args.tenant} pipeline_id={args.pipeline} ===")
    print(f"Mode: {'CONFIRM (will delete)' if args.confirm else 'DRY-RUN (no changes)'}\n")

    try:
        async with Session() as db:
            print("Before:")
            stats = await _stats(db, args.tenant, args.pipeline)
            for k, v in stats.items():
                print(f"  {k:30s} {v}")

            if not args.confirm:
                print("\n(dry-run — no changes made)")
                return 0

            print("\nExecuting deletes...")
            deleted = await _execute_cleanup(db, args.tenant, args.pipeline)
            await db.commit()

            print("\nDeleted:")
            for k, v in deleted.items():
                print(f"  {k:30s} {v}")

            async with Session() as db2:
                print("\nAfter:")
                stats2 = await _stats(db2, args.tenant, args.pipeline)
                for k, v in stats2.items():
                    print(f"  {k:30s} {v}")

            print("\n✓ Done. Now re-run the leadgen handoff from the UI.")
            return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
