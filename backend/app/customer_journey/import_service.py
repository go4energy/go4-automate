"""CSV import service - import contacts + generate ref-codes."""

import csv
import io
import secrets
import string

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.models import Contact
from app.contacts.utils import generate_tracking_hash as _generate_hash
from app.customer_journey.models import JourneyRefCode


def _generate_ref_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# Fields that map directly to Contact columns
DIRECT_FIELD_MAP = {
    "name": "name",
    "email": "email",
    "phone": "phone",
    "mobile": "mobile",
    "position": "position",
    "linkedin": "linkedin",
    "twitter": "twitter",
    "source": "source",
    "notes": "notes",
}

# All mappable target fields (direct + custom_fields)
MAPPABLE_TARGETS = [
    {"key": "name", "label": "Name", "group": "direkt"},
    {"key": "email", "label": "E-Mail", "group": "direkt"},
    {"key": "phone", "label": "Telefon", "group": "direkt"},
    {"key": "mobile", "label": "Mobil", "group": "direkt"},
    {"key": "position", "label": "Position", "group": "direkt"},
    {"key": "linkedin", "label": "LinkedIn URL", "group": "direkt"},
    {"key": "twitter", "label": "Twitter", "group": "direkt"},
    {"key": "source", "label": "Quelle", "group": "direkt"},
    {"key": "notes", "label": "Notizen", "group": "direkt"},
    {"key": "custom_fields", "label": "Custom Field", "group": "custom"},
]


def parse_csv(raw: str) -> tuple[list[str], list[dict[str, str]], csv.Dialect]:
    """Parse CSV string, return (headers, rows as list of dicts, dialect)."""
    # Strip BOM if present
    if raw.startswith("\ufeff"):
        raw = raw[1:]

    # Auto-detect delimiter
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(raw[:2048], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ","

    reader = csv.DictReader(io.StringIO(raw), dialect=dialect)
    headers = reader.fieldnames or []
    rows = list(reader)
    return headers, rows, dialect


class ImportService:
    """Handle CSV contact import with ref-code generation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def preview(
        self,
        tenant_id: str,
        csv_raw: str,
        mapping: dict[str, str],
    ) -> dict:
        """Parse CSV, apply mapping, detect conflicts.

        mapping: {csv_column: target_field} where target_field is either
        a direct field name (e.g. "name", "linkedin") or "custom:fieldname"
        for custom_fields storage.

        Returns: {headers, row_count, preview_rows, conflicts}
        """
        headers, rows, _dialect = parse_csv(csv_raw)

        conflicts = []
        preview_rows = []

        for idx, row in enumerate(rows):
            contact_data = self._apply_mapping(row, mapping)
            if not contact_data.get("name"):
                continue

            # Detect conflict by linkedin URL
            conflict_contact = None
            linkedin_val = contact_data.get("linkedin")
            if linkedin_val:
                result = await self.db.execute(
                    select(Contact).where(
                        Contact.tenant_id == tenant_id,
                        Contact.linkedin == linkedin_val,
                    )
                )
                conflict_contact = result.scalar_one_or_none()

            row_info = {
                "row_index": idx,
                "csv_row": row,
                "mapped_data": contact_data,
            }

            if conflict_contact:
                conflicts.append({
                    **row_info,
                    "existing_contact": {
                        "id": conflict_contact.id,
                        "name": conflict_contact.name,
                        "email": conflict_contact.email,
                        "linkedin": conflict_contact.linkedin,
                        "position": conflict_contact.position,
                    },
                })
            else:
                preview_rows.append(row_info)

        return {
            "headers": headers,
            "row_count": len(rows),
            "new_count": len(preview_rows),
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
            "preview_rows": preview_rows[:10],
        }

    async def execute(
        self,
        tenant_id: str,
        csv_raw: str,
        mapping: dict[str, str],
        base_url: str,
        campaign_id: int | None,
        conflict_resolutions: dict[str, str],
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
    ) -> str:
        """Import contacts, create ref-codes, return CSV with ref_link column.

        conflict_resolutions: {row_index_str: "skip"|"update"|"duplicate"}
        UTM fields are stored on the ref-code for later retrieval by the tracking script.
        """
        headers, rows, dialect = parse_csv(csv_raw)

        created = 0
        updated = 0
        skipped = 0

        # Build output CSV with original data + ref_link, preserving input format
        output = io.StringIO()
        output.write("\ufeff")  # UTF-8 BOM for Excel compatibility
        writer = csv.DictWriter(
            output,
            fieldnames=[*headers, "ref_link"],
            delimiter=dialect.delimiter,
            quotechar=getattr(dialect, "quotechar", '"') or '"',
            quoting=getattr(dialect, "quoting", csv.QUOTE_MINIMAL),
            extrasaction="ignore",
        )
        writer.writeheader()

        for idx, row in enumerate(rows):
            contact_data = self._apply_mapping(row, mapping)
            if not contact_data.get("name"):
                row["ref_link"] = ""
                writer.writerow(row)
                skipped += 1
                continue

            # Check for conflict
            linkedin_val = contact_data.get("linkedin")
            existing = None
            if linkedin_val:
                result = await self.db.execute(
                    select(Contact).where(
                        Contact.tenant_id == tenant_id,
                        Contact.linkedin == linkedin_val,
                    )
                )
                existing = result.scalar_one_or_none()

            contact = None
            resolution = conflict_resolutions.get(str(idx), "create")

            if existing:
                if resolution == "skip":
                    row["ref_link"] = ""
                    writer.writerow(row)
                    skipped += 1
                    continue
                elif resolution == "update":
                    contact = self._update_contact(existing, contact_data)
                    updated += 1
                elif resolution == "duplicate":
                    contact = self._create_contact(tenant_id, contact_data)
                    self.db.add(contact)
                    created += 1
                else:
                    # Default: skip conflicts without explicit resolution
                    row["ref_link"] = ""
                    writer.writerow(row)
                    skipped += 1
                    continue
            else:
                contact = self._create_contact(tenant_id, contact_data)
                self.db.add(contact)
                created += 1

            await self.db.flush()

            # Ensure tracking_hash
            if not contact.tracking_hash:
                contact.tracking_hash = _generate_hash()
                contact.journey_status = contact.journey_status or "new"
                contact.source = contact.source or "csv-import"

            # Generate ref-code
            ref_code = _generate_ref_code()
            ref = JourneyRefCode(
                tenant_id=tenant_id,
                ref_code=ref_code,
                contact_id=contact.id,
                campaign_id=campaign_id,
                name=contact.name,
                target_url=base_url,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
            )
            self.db.add(ref)

            # Build ref link
            sep = "&" if "?" in base_url else "?"
            ref_link = f"{base_url}{sep}ref={ref_code}"

            row["ref_link"] = ref_link
            writer.writerow(row)

        await self.db.flush()

        logger.info(
            "CSV Import: {created} erstellt, {updated} aktualisiert, {skipped} übersprungen",
            created=created,
            updated=updated,
            skipped=skipped,
        )

        output.seek(0)
        return output.getvalue()

    @staticmethod
    def _apply_mapping(
        row: dict[str, str], mapping: dict[str, str],
    ) -> dict:
        """Apply column mapping to a CSV row, return contact field dict."""
        result: dict = {"custom_fields": {}}

        for csv_col, target in mapping.items():
            value = row.get(csv_col, "").strip()
            if not value:
                continue

            if target.startswith("custom:"):
                field_name = target[7:]
                result["custom_fields"][field_name] = value
            elif target in DIRECT_FIELD_MAP:
                result[target] = value

        # Fallback: build name from first_name + last_name if no name mapped
        if not result.get("name"):
            parts = []
            for csv_col, target in mapping.items():
                if target == "_first_name":
                    parts.insert(0, row.get(csv_col, "").strip())
                elif target == "_last_name":
                    parts.append(row.get(csv_col, "").strip())
            if parts:
                result["name"] = " ".join(p for p in parts if p)

        return result

    @staticmethod
    def _create_contact(tenant_id: str, data: dict) -> Contact:
        """Create a new Contact from mapped data."""
        # Email is required (NOT NULL), generate placeholder if missing
        email = data.get("email") or f"import-{_generate_hash(8)}@placeholder.local"

        return Contact(
            tenant_id=tenant_id,
            name=data.get("name", "Unbekannt"),
            email=email,
            phone=data.get("phone"),
            mobile=data.get("mobile"),
            position=data.get("position"),
            linkedin=data.get("linkedin"),
            twitter=data.get("twitter"),
            source=data.get("source", "csv-import"),
            notes=data.get("notes"),
            custom_fields=data.get("custom_fields", {}),
            tracking_hash=_generate_hash(),
            journey_status="new",
        )

    @staticmethod
    def _update_contact(contact: Contact, data: dict) -> Contact:
        """Update existing contact with mapped data (non-empty fields only)."""
        for field in ("name", "phone", "mobile", "position", "twitter",
                      "source", "notes"):
            val = data.get(field)
            if val:
                setattr(contact, field, val)

        # Merge custom_fields
        if data.get("custom_fields"):
            merged = {**(contact.custom_fields or {}), **data["custom_fields"]}
            contact.custom_fields = merged

        # Ensure tracking hash
        if not contact.tracking_hash:
            contact.tracking_hash = _generate_hash()
            contact.journey_status = contact.journey_status or "new"

        return contact
