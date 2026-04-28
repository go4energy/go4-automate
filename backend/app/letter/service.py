"""Letter Module Service.

Business logic for letter management, template rendering,
and batch processing.
"""

import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from jinja2 import Template
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.models import Contact
from app.engagement.activity_helper import Channel, Direction, log_activity
from app.letter.models import (
    BatchStatus,
    Letter,
    LetterBatch,
    LetterStatus,
    LetterTemplate,
)
from app.letter.schemas import RecipientData


class LetterService:
    """Service für Brief-Management."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        # Base path for generated files
        self.output_dir = Path("data/letter")

    # ============== Templates ==============

    async def list_templates(
        self,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LetterTemplate], int]:
        """List templates with pagination."""
        query = select(LetterTemplate).where(
            LetterTemplate.tenant_id == self.tenant_id
        )

        if active_only:
            query = query.where(LetterTemplate.is_active.is_(True))

        # Count
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Fetch
        query = query.order_by(LetterTemplate.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        templates = list(result.scalars().all())

        return templates, total

    async def get_template(self, template_id: int) -> LetterTemplate | None:
        """Get template by ID."""
        result = await self.db.execute(
            select(LetterTemplate).where(
                LetterTemplate.id == template_id,
                LetterTemplate.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_template(
        self,
        name: str,
        content_html: str,
        description: str | None = None,
        format: str = "a4",
        header_html: str | None = None,
        footer_html: str | None = None,
    ) -> LetterTemplate:
        """Create a new template."""
        template = LetterTemplate(
            tenant_id=self.tenant_id,
            name=name,
            description=description,
            format=format,
            content_html=content_html,
            header_html=header_html,
            footer_html=footer_html,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        logger.info(f"Created letter template: {template.id}")
        return template

    async def update_template(
        self,
        template_id: int,
        **kwargs,
    ) -> LetterTemplate | None:
        """Update a template."""
        template = await self.get_template(template_id)
        if not template:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(template, key):
                setattr(template, key, value)

        template.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete_template(self, template_id: int) -> bool:
        """Delete a template (soft delete by deactivating)."""
        template = await self.get_template(template_id)
        if not template:
            return False

        template.is_active = False
        template.updated_at = datetime.now(UTC)
        await self.db.commit()
        return True

    # ============== Letters ==============

    async def list_letters(
        self,
        status: str | None = None,
        batch_id: int | None = None,
        contact_id: int | None = None,
        pipeline_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Letter], int]:
        """List letters with filters."""
        query = (
            select(Letter)
            .options(selectinload(Letter.template))
            .where(Letter.tenant_id == self.tenant_id)
        )

        if status:
            query = query.where(Letter.status == status)
        if batch_id:
            query = query.where(Letter.batch_id == batch_id)
        if contact_id:
            query = query.where(Letter.contact_id == contact_id)
        if pipeline_id is not None:
            query = query.where(Letter.pipeline_id == pipeline_id)

        # Count
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Fetch
        query = query.order_by(Letter.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        letters = list(result.scalars().all())

        return letters, total

    async def get_letter(self, letter_id: int) -> Letter | None:
        """Get letter by ID."""
        result = await self.db.execute(
            select(Letter)
            .options(selectinload(Letter.template))
            .where(
                Letter.id == letter_id,
                Letter.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_letter(
        self,
        template_id: int,
        recipient: RecipientData,
        contact_id: int | None = None,
        pipeline_id: int | None = None,
        content_html: str | None = None,
    ) -> Letter:
        """Create a new letter."""
        # Verify template exists
        template = await self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        letter = Letter(
            tenant_id=self.tenant_id,
            template_id=template_id,
            contact_id=contact_id,
            pipeline_id=pipeline_id,
            recipient_name=recipient.name,
            recipient_company=recipient.company,
            recipient_street=recipient.street,
            recipient_zip=recipient.zip,
            recipient_city=recipient.city,
            recipient_country=recipient.country,
            content_html=content_html,
            status=LetterStatus.DRAFT,
        )
        self.db.add(letter)
        await self.db.commit()
        await self.db.refresh(letter)
        logger.info(f"Created letter: {letter.id}")
        return letter

    async def create_letter_from_contact(
        self,
        template_id: int,
        contact_id: int,
        pipeline_id: int | None = None,
    ) -> Letter:
        """Create letter with contact's address."""
        # Get contact
        result = await self.db.execute(
            select(Contact).where(
                Contact.id == contact_id,
                Contact.tenant_id == self.tenant_id,
            )
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise ValueError(f"Contact {contact_id} not found")

        # Get template
        template = await self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Build recipient from contact
        address = contact.address or {}
        recipient = RecipientData(
            name=f"{contact.first_name or ''} {contact.last_name or ''}".strip()
            or "Unbekannt",
            company=contact.company,
            street=address.get("street"),
            zip=address.get("zip"),
            city=address.get("city"),
            country=address.get("country", "DE"),
        )

        # Render content
        content_html = await self.render_template(template, contact)

        return await self.create_letter(
            template_id=template_id,
            recipient=recipient,
            contact_id=contact_id,
            pipeline_id=pipeline_id,
            content_html=content_html,
        )

    async def update_letter(
        self,
        letter_id: int,
        **kwargs,
    ) -> Letter | None:
        """Update a letter."""
        letter = await self.get_letter(letter_id)
        if not letter:
            return None

        # Handle recipient update
        if kwargs.get("recipient"):
            recipient = kwargs.pop("recipient")
            letter.recipient_name = recipient.name
            letter.recipient_company = recipient.company
            letter.recipient_street = recipient.street
            letter.recipient_zip = recipient.zip
            letter.recipient_city = recipient.city
            letter.recipient_country = recipient.country

        for key, value in kwargs.items():
            if value is not None and hasattr(letter, key):
                setattr(letter, key, value)

        letter.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(letter)
        return letter

    async def approve_letter(self, letter_id: int) -> Letter | None:
        """Approve a draft letter."""
        letter = await self.get_letter(letter_id)
        if not letter or letter.status != LetterStatus.DRAFT:
            return None

        letter.status = LetterStatus.APPROVED
        letter.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(letter)
        return letter

    async def delete_letter(self, letter_id: int) -> bool:
        """Delete a draft letter."""
        letter = await self.get_letter(letter_id)
        if not letter or letter.status != LetterStatus.DRAFT:
            return False

        await self.db.delete(letter)
        await self.db.commit()
        return True

    # ============== Template Rendering ==============

    async def render_template(
        self,
        template: LetterTemplate,
        contact: Contact | None = None,
        custom_data: dict | None = None,
    ) -> str:
        """Render template with contact data and custom variables."""
        context = {
            "date": datetime.now().strftime("%d.%m.%Y"),
            "year": datetime.now().strftime("%Y"),
        }

        if contact:
            context["contact"] = {
                "name": f"{contact.first_name or ''} {contact.last_name or ''}".strip(),
                "first_name": contact.first_name or "",
                "last_name": contact.last_name or "",
                "company": contact.company or "",
                "position": contact.position or "",
                "email": contact.email or "",
            }

        if custom_data:
            context.update(custom_data)

        try:
            jinja_template = Template(template.content_html)
            return jinja_template.render(**context)
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            return template.content_html

    async def render_preview(
        self,
        template_id: int,
        contact_id: int | None = None,
        custom_data: dict | None = None,
    ) -> tuple[str, RecipientData | None]:
        """Render template preview with optional contact."""
        template = await self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        contact = None
        recipient = None

        if contact_id:
            result = await self.db.execute(
                select(Contact).where(
                    Contact.id == contact_id,
                    Contact.tenant_id == self.tenant_id,
                )
            )
            contact = result.scalar_one_or_none()
            if contact:
                address = contact.address or {}
                recipient = RecipientData(
                    name=f"{contact.first_name or ''} {contact.last_name or ''}".strip()
                    or "Unbekannt",
                    company=contact.company,
                    street=address.get("street"),
                    zip=address.get("zip"),
                    city=address.get("city"),
                    country=address.get("country", "DE"),
                )

        html = await self.render_template(template, contact, custom_data)
        return html, recipient

    # ============== PDF Generation ==============

    async def generate_pdf(self, letter_id: int) -> str:
        """Generate PDF from letter content."""
        letter = await self.get_letter(letter_id)
        if not letter:
            raise ValueError(f"Letter {letter_id} not found")

        template = letter.template

        # Build full HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ size: A4; margin: 2cm; }}
                body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.5; }}
                .header {{ margin-bottom: 2cm; }}
                .footer {{ margin-top: 2cm; font-size: 9pt; color: #666; }}
                .content {{ min-height: 15cm; }}
            </style>
        </head>
        <body>
            <div class="header">{template.header_html or ''}</div>
            <div class="content">{letter.content_html or ''}</div>
            <div class="footer">{template.footer_html or ''}</div>
        </body>
        </html>
        """

        # Create output directory
        output_dir = self.output_dir / self.tenant_id / "letters"
        output_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = output_dir / f"letter_{letter.id}.pdf"

        try:
            # Try WeasyPrint if available
            from weasyprint import HTML

            HTML(string=html).write_pdf(str(pdf_path))
            logger.info(f"Generated PDF: {pdf_path}")
        except ImportError:
            # Fallback: Save HTML instead
            html_path = output_dir / f"letter_{letter.id}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            pdf_path = html_path
            logger.warning(f"WeasyPrint not available, saved HTML: {html_path}")

        # Update letter
        letter.pdf_path = str(pdf_path)
        letter.updated_at = datetime.now(UTC)
        await self.db.commit()

        return str(pdf_path)

    # ============== Batches ==============

    async def list_batches(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LetterBatch], int]:
        """List batches with filters."""
        query = select(LetterBatch).where(LetterBatch.tenant_id == self.tenant_id)

        if status:
            query = query.where(LetterBatch.status == status)

        # Count
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Fetch
        query = query.order_by(LetterBatch.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        batches = list(result.scalars().all())

        return batches, total

    async def get_batch(self, batch_id: int) -> LetterBatch | None:
        """Get batch by ID."""
        result = await self.db.execute(
            select(LetterBatch).where(
                LetterBatch.id == batch_id,
                LetterBatch.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_batch(
        self,
        name: str,
        letter_ids: list[int],
    ) -> LetterBatch:
        """Create a batch from letters."""
        batch = LetterBatch(
            tenant_id=self.tenant_id,
            name=name,
            letter_count=len(letter_ids),
            status=BatchStatus.COLLECTING,
        )
        self.db.add(batch)
        await self.db.flush()

        # Assign letters to batch
        for letter_id in letter_ids:
            letter = await self.get_letter(letter_id)
            if letter and letter.status in (LetterStatus.DRAFT, LetterStatus.APPROVED):
                letter.batch_id = batch.id
                letter.status = LetterStatus.QUEUED
                letter.queued_at = datetime.now(UTC)

        batch.status = BatchStatus.READY
        await self.db.commit()
        await self.db.refresh(batch)
        logger.info(
            f"Created letter batch: {batch.id} with {len(letter_ids)} letters"
        )
        return batch

    async def export_batch(self, batch_id: int) -> str:
        """Export batch as CSV for lettershop."""
        batch = await self.get_batch(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        # Get letters
        letters, _ = await self.list_letters(batch_id=batch_id, limit=10000)

        # Generate PDF for each letter if not done
        for letter in letters:
            if not letter.pdf_path:
                await self.generate_pdf(letter.id)

        # Create CSV
        output = StringIO()
        writer = csv.writer(output, delimiter=";")

        # Header
        writer.writerow(
            [
                "name",
                "company",
                "street",
                "zip",
                "city",
                "country",
                "pdf_path",
            ]
        )

        # Data
        for letter in letters:
            writer.writerow(
                [
                    letter.recipient_name,
                    letter.recipient_company or "",
                    letter.recipient_street or "",
                    letter.recipient_zip or "",
                    letter.recipient_city or "",
                    letter.recipient_country,
                    letter.pdf_path or "",
                ]
            )

        # Save CSV
        output_dir = self.output_dir / self.tenant_id / "exports"
        output_dir.mkdir(parents=True, exist_ok=True)
        export_path = output_dir / f"batch_{batch.id}.csv"

        with open(export_path, "w", encoding="utf-8") as f:
            f.write(output.getvalue())

        # Update batch
        batch.export_format = "csv"
        batch.export_path = str(export_path)
        batch.exported_at = datetime.now(UTC)
        batch.status = BatchStatus.EXPORTED
        await self.db.commit()

        logger.info(f"Exported batch {batch_id} to {export_path}")
        return str(export_path)

    async def mark_batch_sent(self, batch_id: int) -> LetterBatch | None:
        """Mark batch as sent."""
        batch = await self.get_batch(batch_id)
        if not batch or batch.status != BatchStatus.EXPORTED:
            return None

        batch.status = BatchStatus.SENT
        batch.sent_at = datetime.now(UTC)

        # Update all letters and log activities
        letters, _ = await self.list_letters(batch_id=batch_id, limit=10000)
        for letter in letters:
            letter.status = LetterStatus.SENT
            letter.sent_at = datetime.now(UTC)

            # Log activity for letters with contact
            if letter.contact_id:
                try:
                    await log_activity(
                        db=self.db,
                        tenant_id=self.tenant_id,
                        contact_id=letter.contact_id,
                        channel=Channel.LETTER,
                        activity_type="letter_sent",
                        direction=Direction.OUTBOUND,
                        subject=f"Brief versendet: {letter.recipient_name}",
                        content=letter.content_html[:500] if letter.content_html else None,
                        source_module="letter",
                        pipeline_id=letter.pipeline_id,
                        metadata={"letter_id": letter.id, "batch_id": batch_id},
                        commit=False,
                    )
                except Exception as e:
                    logger.warning(f"Activity logging failed for letter {letter.id}: {e}")

        await self.db.commit()
        await self.db.refresh(batch)
        return batch

    # ============== Stats ==============

    async def get_stats(self) -> dict:
        """Get letter statistics."""
        # Templates
        result = await self.db.execute(
            select(func.count()).where(LetterTemplate.tenant_id == self.tenant_id)
        )
        total_templates = result.scalar() or 0

        result = await self.db.execute(
            select(func.count()).where(
                LetterTemplate.tenant_id == self.tenant_id,
                LetterTemplate.is_active.is_(True),
            )
        )
        active_templates = result.scalar() or 0

        # Letters
        result = await self.db.execute(
            select(func.count()).where(Letter.tenant_id == self.tenant_id)
        )
        total_letters = result.scalar() or 0

        # Letters by status
        result = await self.db.execute(
            select(Letter.status, func.count())
            .where(Letter.tenant_id == self.tenant_id)
            .group_by(Letter.status)
        )
        letters_by_status = {row[0]: row[1] for row in result.all()}

        # Batches
        result = await self.db.execute(
            select(func.count()).where(LetterBatch.tenant_id == self.tenant_id)
        )
        total_batches = result.scalar() or 0

        result = await self.db.execute(
            select(func.count()).where(
                LetterBatch.tenant_id == self.tenant_id,
                LetterBatch.status.in_([BatchStatus.COLLECTING, BatchStatus.READY]),
            )
        )
        pending_batches = result.scalar() or 0

        return {
            "total_templates": total_templates,
            "active_templates": active_templates,
            "total_letters": total_letters,
            "letters_by_status": letters_by_status,
            "total_batches": total_batches,
            "pending_batches": pending_batches,
        }
