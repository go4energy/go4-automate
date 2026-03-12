"""LinkedIn service - CRUD and business logic for accounts, jobs, contacts."""

from datetime import datetime

from cryptography.fernet import Fernet
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.exceptions import NotFoundError, ValidationError
from app.funnels.dedup import compute_dedup_keys
from app.funnels.models import Funnel, FunnelCompany, FunnelProspect
from app.linkedin.models import (
    LinkedInAccount,
    LinkedInContact,
    LinkedInJobLog,
    LinkedInScraperJob,
)
from app.linkedin.schemas import (
    LinkedInAccountCreate,
    LinkedInAccountUpdate,
    LinkedInImportRequest,
    LinkedInImportResult,
    LinkedInJobCreate,
    LinkedInJobUpdate,
    LinkedInManualUrlImport,
    LinkedInManualUrlImportResult,
)


def get_fernet() -> Fernet:
    """Get Fernet instance for encryption."""
    import base64

    key = getattr(settings, "ENCRYPTION_KEY", None)
    if not key:
        # Derive a stable Fernet key from secret_key
        raw = settings.secret_key.encode()[:32].ljust(32, b"\0")
        key = base64.urlsafe_b64encode(raw)
    return Fernet(key if isinstance(key, bytes) else key.encode())


class AccountService:
    """Service for LinkedIn account management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _encrypt_password(self, password: str) -> str:
        """Encrypt password using Fernet."""
        fernet = get_fernet()
        return fernet.encrypt(password.encode()).decode()

    def _decrypt_password(self, encrypted: str) -> str:
        """Decrypt password using Fernet."""
        fernet = get_fernet()
        return fernet.decrypt(encrypted.encode()).decode()

    async def create(
        self, tenant_id: str, data: LinkedInAccountCreate
    ) -> LinkedInAccount:
        """Create a new LinkedIn account."""
        password_encrypted = None
        if data.password:
            password_encrypted = self._encrypt_password(data.password)

        account = LinkedInAccount(
            tenant_id=tenant_id,
            name=data.name,
            email=data.email,
            password_encrypted=password_encrypted,
            is_sales_navigator=data.is_sales_navigator,
            daily_profile_limit=data.daily_profile_limit,
            status="inactive",
        )
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        logger.info("LinkedIn Account erstellt: {name}", name=data.name)
        return account

    async def get_by_id(self, tenant_id: str, account_id: int) -> LinkedInAccount:
        """Get an account by ID."""
        result = await self.db.execute(
            select(LinkedInAccount)
            .options(selectinload(LinkedInAccount.scraper_jobs))
            .where(
                LinkedInAccount.id == account_id,
                LinkedInAccount.tenant_id == tenant_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundError("LinkedInAccount", account_id)
        return account

    async def list_accounts(
        self, tenant_id: str, status: str | None = None
    ) -> list[LinkedInAccount]:
        """List all accounts for a tenant."""
        query = (
            select(LinkedInAccount)
            .options(selectinload(LinkedInAccount.scraper_jobs))
            .where(LinkedInAccount.tenant_id == tenant_id)
        )

        if status:
            query = query.where(LinkedInAccount.status == status)

        query = query.order_by(LinkedInAccount.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, account_id: int, data: LinkedInAccountUpdate
    ) -> LinkedInAccount:
        """Update a LinkedIn account."""
        account = await self.get_by_id(tenant_id, account_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle password separately
        if update_data.get("password"):
            update_data["password_encrypted"] = self._encrypt_password(
                update_data.pop("password")
            )
        elif "password" in update_data:
            del update_data["password"]

        for key, value in update_data.items():
            setattr(account, key, value)

        await self.db.flush()
        await self.db.refresh(account)
        logger.info("LinkedIn Account aktualisiert: {id}", id=account_id)
        return account

    async def delete(self, tenant_id: str, account_id: int) -> None:
        """Delete a LinkedIn account."""
        account = await self.get_by_id(tenant_id, account_id)

        # Check for running jobs
        running_jobs = await self.db.execute(
            select(func.count(LinkedInScraperJob.id)).where(
                LinkedInScraperJob.account_id == account_id,
                LinkedInScraperJob.status.in_(["running", "queued"]),
            )
        )
        if running_jobs.scalar() > 0:
            raise ValidationError(
                "Account kann nicht gelöscht werden, da noch Jobs laufen"
            )

        await self.db.delete(account)
        await self.db.flush()
        logger.info("LinkedIn Account gelöscht: {id}", id=account_id)

    async def reset_daily_counter(self, tenant_id: str, account_id: int) -> None:
        """Reset daily profile counter (called at midnight or manually)."""
        account = await self.get_by_id(tenant_id, account_id)
        account.profiles_scraped_today = 0
        account.last_scrape_date = datetime.utcnow()
        await self.db.flush()

    async def update_session(
        self,
        tenant_id: str,
        account_id: int,
        session_data: dict,
        expires_at: datetime,
    ) -> LinkedInAccount:
        """Update session data after login."""
        account = await self.get_by_id(tenant_id, account_id)
        account.session_data = session_data
        account.session_expires_at = expires_at
        account.last_login_at = datetime.utcnow()
        account.status = "active"
        account.last_error = None
        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def mark_session_invalid(
        self, tenant_id: str, account_id: int, error: str
    ) -> None:
        """Mark session as invalid."""
        account = await self.get_by_id(tenant_id, account_id)
        account.status = "inactive"
        account.last_error = error
        await self.db.flush()


class JobService:
    """Service for LinkedIn scraper job management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, tenant_id: str, data: LinkedInJobCreate
    ) -> LinkedInScraperJob:
        """Create a new scraper job."""
        # Validate account exists
        account_result = await self.db.execute(
            select(LinkedInAccount).where(
                LinkedInAccount.id == data.account_id,
                LinkedInAccount.tenant_id == tenant_id,
            )
        )
        account = account_result.scalar_one_or_none()
        if not account:
            raise NotFoundError("LinkedInAccount", data.account_id)

        # Validate funnel if specified
        if data.funnel_id:
            funnel_result = await self.db.execute(
                select(Funnel).where(
                    Funnel.id == data.funnel_id,
                    Funnel.tenant_id == tenant_id,
                )
            )
            if not funnel_result.scalar_one_or_none():
                raise NotFoundError("Funnel", data.funnel_id)

        job = LinkedInScraperJob(
            tenant_id=tenant_id,
            account_id=data.account_id,
            funnel_id=data.funnel_id,
            pipeline_id=data.pipeline_id,
            name=data.name,
            job_type=data.job_type,
            search_url=data.search_url,
            profile_urls=data.profile_urls,
            max_profiles=data.max_profiles,
            daily_limit=data.daily_limit,
            min_delay_seconds=data.min_delay_seconds,
            max_delay_seconds=data.min_delay_seconds,
            scrape_full_profiles=data.scrape_full_profiles,
            auto_import=data.auto_import,
            import_stage_id=data.import_stage_id,
            auto_enroll_pipeline=data.auto_enroll_pipeline,
            # Schedule settings
            schedule_enabled=data.schedule_enabled,
            schedule_days=data.schedule_days,
            schedule_start_time=data.schedule_start_time,
            schedule_end_time=data.schedule_end_time,
            max_pages_per_run=data.max_pages_per_run,
            connections_since_date=data.connections_since_date,
            status="draft",
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        logger.info("LinkedIn Job erstellt: {name}", name=data.name)
        return job

    async def get_by_id(self, tenant_id: str, job_id: int) -> LinkedInScraperJob:
        """Get a job by ID with related data."""
        result = await self.db.execute(
            select(LinkedInScraperJob)
            .options(
                selectinload(LinkedInScraperJob.account),
                selectinload(LinkedInScraperJob.funnel),
                selectinload(LinkedInScraperJob.pipeline),
                selectinload(LinkedInScraperJob.import_stage),
            )
            .where(
                LinkedInScraperJob.id == job_id,
                LinkedInScraperJob.tenant_id == tenant_id,
            )
        )
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError("LinkedInScraperJob", job_id)
        return job

    async def list_jobs(
        self,
        tenant_id: str,
        account_id: int | None = None,
        status: str | None = None,
    ) -> list[LinkedInScraperJob]:
        """List all jobs for a tenant."""
        query = (
            select(LinkedInScraperJob)
            .options(
                selectinload(LinkedInScraperJob.account),
                selectinload(LinkedInScraperJob.funnel),
                selectinload(LinkedInScraperJob.pipeline),
            )
            .where(LinkedInScraperJob.tenant_id == tenant_id)
        )

        if account_id:
            query = query.where(LinkedInScraperJob.account_id == account_id)
        if status:
            query = query.where(LinkedInScraperJob.status == status)

        query = query.order_by(LinkedInScraperJob.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, job_id: int, data: LinkedInJobUpdate
    ) -> LinkedInScraperJob:
        """Update a scraper job."""
        job = await self.get_by_id(tenant_id, job_id)

        if job.status in ["running", "queued"]:
            raise ValidationError("Job kann nicht bearbeitet werden, während er läuft")

        update_data = data.model_dump(exclude_unset=True)

        # Sync max_delay to min_delay (single delay value in frontend)
        if "min_delay_seconds" in update_data:
            update_data["max_delay_seconds"] = update_data["min_delay_seconds"]

        for key, value in update_data.items():
            setattr(job, key, value)

        await self.db.flush()
        await self.db.refresh(job)
        logger.info("LinkedIn Job aktualisiert: {id}", id=job_id)
        return job

    async def delete(self, tenant_id: str, job_id: int) -> None:
        """Delete a scraper job."""
        job = await self.get_by_id(tenant_id, job_id)

        if job.status == "running":
            raise ValidationError("Job kann nicht gelöscht werden, während er läuft")

        await self.db.delete(job)
        await self.db.flush()
        logger.info("LinkedIn Job gelöscht: {id}", id=job_id)

    async def start_job(self, tenant_id: str, job_id: int) -> LinkedInScraperJob:
        """Queue a job for execution."""
        job = await self.get_by_id(tenant_id, job_id)

        if job.status not in ["draft", "paused", "failed", "cancelled", "completed"]:
            raise ValidationError(
                f"Job kann nicht gestartet werden (Status: {job.status})"
            )

        # Account-Status prüfen, aber nicht blockieren —
        # Worker öffnet Browser und User kann sich manuell einloggen
        if job.account.status not in ("active", "inactive", "session_expired"):
            logger.warning(
                "Account {email} hat Status {status}, Job wird trotzdem gestartet",
                email=job.account.email,
                status=job.account.status,
            )

        job.status = "queued"
        job.error_message = None
        if not job.started_at:
            job.started_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(job)
        logger.info("LinkedIn Job in Queue: {id}", id=job_id)
        return job

    async def pause_job(self, tenant_id: str, job_id: int) -> LinkedInScraperJob:
        """Pause a running or queued job."""
        from app.linkedin.debug_bridge import bridge

        job = await self.get_by_id(tenant_id, job_id)

        if job.status not in ["running", "queued"]:
            raise ValidationError(
                f"Job kann nicht pausiert werden (Status: {job.status})"
            )

        job.status = "paused"
        await self.db.flush()
        await self.db.refresh(job)

        # Signal the debug bridge to unblock the worker
        bridge.cancel()
        logger.info("LinkedIn Job pausiert: {id}", id=job_id)
        return job

    async def cancel_job(self, tenant_id: str, job_id: int) -> LinkedInScraperJob:
        """Cancel a job."""
        from app.linkedin.debug_bridge import bridge

        job = await self.get_by_id(tenant_id, job_id)

        if job.status == "completed":
            raise ValidationError("Abgeschlossener Job kann nicht abgebrochen werden")

        job.status = "cancelled"
        job.completed_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(job)

        # Signal the debug bridge to unblock the worker
        bridge.cancel()
        logger.info("LinkedIn Job abgebrochen: {id}", id=job_id)
        return job

    async def add_manual_urls(
        self, tenant_id: str, job_id: int, data: LinkedInManualUrlImport
    ) -> LinkedInManualUrlImportResult:
        """Add profile URLs manually to a job."""
        job = await self.get_by_id(tenant_id, job_id)

        if job.job_type != "profile_list":
            raise ValidationError(
                "URLs können nur zu Profile-List Jobs hinzugefügt werden"
            )

        existing_urls = set(job.profile_urls or [])
        added = 0
        duplicates = 0
        invalid = 0
        errors = []

        for url in data.urls:
            # Basic URL validation
            url = url.strip()
            if not url.startswith("http"):
                invalid += 1
                errors.append(f"Ungültige URL: {url[:50]}")
                continue

            if "linkedin.com" not in url:
                invalid += 1
                errors.append(f"Keine LinkedIn URL: {url[:50]}")
                continue

            if url in existing_urls:
                duplicates += 1
                continue

            existing_urls.add(url)
            added += 1

        job.profile_urls = list(existing_urls)
        job.profiles_found = len(existing_urls)
        await self.db.flush()
        await self.db.refresh(job)

        logger.info(
            "LinkedIn Job URLs hinzugefügt: {id} ({added} neu)",
            id=job_id,
            added=added,
        )

        return LinkedInManualUrlImportResult(
            total=len(data.urls),
            added=added,
            duplicates=duplicates,
            invalid=invalid,
            errors=errors[:10],
        )


class JobLogService:
    """Service for LinkedIn job execution logs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        tenant_id: str,
        job_id: int,
        start_page: int = 1,
    ) -> LinkedInJobLog:
        """Create a new job log entry (when a job run starts)."""
        log = LinkedInJobLog(
            tenant_id=tenant_id,
            job_id=job_id,
            started_at=datetime.utcnow(),
            start_page=start_page,
            status="running",
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        logger.info("LinkedIn Job Log erstellt: job={job} page={page}", job=job_id, page=start_page)
        return log

    async def complete(
        self,
        log_id: int,
        end_page: int,
        profiles_scraped: int,
        profiles_failed: int,
        profiles_skipped: int = 0,
        error_message: str | None = None,
    ) -> LinkedInJobLog:
        """Mark a job log as completed."""
        result = await self.db.execute(
            select(LinkedInJobLog).where(LinkedInJobLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            raise NotFoundError("LinkedInJobLog", log_id)

        log.completed_at = datetime.utcnow()
        log.end_page = end_page
        log.profiles_scraped = profiles_scraped
        log.profiles_failed = profiles_failed
        log.profiles_skipped = profiles_skipped
        log.status = "failed" if error_message else "completed"
        log.error_message = error_message

        # Calculate duration
        if log.started_at:
            duration = (log.completed_at - log.started_at).total_seconds()
            log.duration_seconds = int(duration)

        await self.db.flush()
        await self.db.refresh(log)
        logger.info(
            "LinkedIn Job Log abgeschlossen: id={id} status={status} profiles={profiles}",
            id=log_id,
            status=log.status,
            profiles=profiles_scraped,
        )
        return log

    async def list_for_job(self, job_id: int, limit: int = 20) -> list[LinkedInJobLog]:
        """List logs for a job, newest first."""
        result = await self.db.execute(
            select(LinkedInJobLog)
            .where(LinkedInJobLog.job_id == job_id)
            .order_by(LinkedInJobLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, job_id: int, log_id: int) -> LinkedInJobLog:
        """Get a specific log entry."""
        result = await self.db.execute(
            select(LinkedInJobLog).where(
                LinkedInJobLog.id == log_id,
                LinkedInJobLog.job_id == job_id,
            )
        )
        log = result.scalar_one_or_none()
        if not log:
            raise NotFoundError("LinkedInJobLog", log_id)
        return log

    async def get_last_for_job(self, job_id: int) -> LinkedInJobLog | None:
        """Get the most recent log for a job."""
        result = await self.db.execute(
            select(LinkedInJobLog)
            .where(LinkedInJobLog.job_id == job_id)
            .order_by(LinkedInJobLog.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class ContactService:
    """Service for LinkedIn contact management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, tenant_id: str, contact_id: int) -> LinkedInContact:
        """Get a contact by ID."""
        result = await self.db.execute(
            select(LinkedInContact)
            .options(
                selectinload(LinkedInContact.scraper_job),
                selectinload(LinkedInContact.funnel_prospect),
            )
            .where(
                LinkedInContact.id == contact_id,
                LinkedInContact.tenant_id == tenant_id,
            )
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise NotFoundError("LinkedInContact", contact_id)
        return contact

    async def list_contacts(
        self,
        tenant_id: str,
        job_id: int | None = None,
        status: str | None = None,
        imported: bool | None = None,
    ) -> list[LinkedInContact]:
        """List contacts."""
        query = select(LinkedInContact).where(LinkedInContact.tenant_id == tenant_id)

        if job_id:
            query = query.where(LinkedInContact.scraper_job_id == job_id)
        if status:
            query = query.where(LinkedInContact.status == status)
        if imported is True:
            query = query.where(LinkedInContact.funnel_prospect_id.isnot(None))
        elif imported is False:
            query = query.where(LinkedInContact.funnel_prospect_id.is_(None))

        query = query.order_by(LinkedInContact.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_for_job(self, tenant_id: str, job_id: int) -> list[LinkedInContact]:
        """List all contacts for a job."""
        return await self.list_contacts(tenant_id, job_id=job_id)

    async def import_to_funnel(
        self, tenant_id: str, job_id: int, data: LinkedInImportRequest
    ) -> LinkedInImportResult:
        """Import LinkedIn contacts to a funnel as prospects."""
        # Validate funnel
        funnel_result = await self.db.execute(
            select(Funnel)
            .options(selectinload(Funnel.stages))
            .where(Funnel.id == data.funnel_id, Funnel.tenant_id == tenant_id)
        )
        funnel = funnel_result.scalar_one_or_none()
        if not funnel:
            raise NotFoundError("Funnel", data.funnel_id)

        # Get stage
        stage_id = data.stage_id
        if not stage_id:
            first_stage = min(funnel.stages, key=lambda s: s.position, default=None)
            if first_stage:
                stage_id = first_stage.id

        # Get contacts to import
        query = select(LinkedInContact).where(
            LinkedInContact.scraper_job_id == job_id,
            LinkedInContact.tenant_id == tenant_id,
            LinkedInContact.status == "scraped",
        )
        if data.contact_ids:
            query = query.where(LinkedInContact.id.in_(data.contact_ids))

        result = await self.db.execute(query)
        contacts = list(result.scalars().all())

        imported = 0
        skipped = 0
        duplicates = 0
        companies_created = 0
        errors = []
        prospect_ids = []

        for contact in contacts:
            try:
                # Check for duplicates by LinkedIn URL
                if data.skip_duplicates and contact.linkedin_url:
                    dedup_keys = compute_dedup_keys(
                        linkedin_url=contact.linkedin_url,
                        email=contact.email,
                    )
                    existing = await self.db.execute(
                        select(FunnelProspect).where(
                            FunnelProspect.tenant_id == tenant_id,
                            FunnelProspect.funnel_id == data.funnel_id,
                            FunnelProspect.dedup_linkedin
                            == dedup_keys.get("dedup_linkedin"),
                        )
                    )
                    if existing.scalar_one_or_none():
                        duplicates += 1
                        contact.status = "skipped"
                        continue

                # Create or find company
                company_id = None
                if data.create_companies and contact.company_name:
                    # Find existing company by name in funnel
                    company_result = await self.db.execute(
                        select(FunnelCompany).where(
                            FunnelCompany.tenant_id == tenant_id,
                            FunnelCompany.funnel_id == data.funnel_id,
                            FunnelCompany.name == contact.company_name,
                        )
                    )
                    company = company_result.scalar_one_or_none()
                    if not company:
                        company = FunnelCompany(
                            tenant_id=tenant_id,
                            funnel_id=data.funnel_id,
                            name=contact.company_name,
                            industry=contact.company_industry,
                            size=contact.company_size,
                            source="linkedin",
                        )
                        self.db.add(company)
                        await self.db.flush()
                        companies_created += 1
                    company_id = company.id
                    contact.funnel_company_id = company_id

                # Create prospect
                dedup_keys = compute_dedup_keys(
                    email=contact.email,
                    linkedin_url=contact.linkedin_url,
                    phone=contact.phone,
                )

                prospect = FunnelProspect(
                    tenant_id=tenant_id,
                    funnel_id=data.funnel_id,
                    company_id=company_id,
                    stage_id=stage_id,
                    name=contact.name,
                    first_name=contact.first_name,
                    last_name=contact.last_name,
                    email=contact.email,
                    phone=contact.phone,
                    position=contact.position,
                    linkedin_url=contact.linkedin_url,
                    twitter_url=contact.twitter_url,
                    source="linkedin",
                    source_id=str(contact.id),
                    custom_fields={
                        "linkedin_headline": contact.headline,
                        "location": contact.location,
                    },
                    enrichment_data={
                        "experience": contact.experience,
                        "education": contact.education,
                        "skills": contact.skills,
                    },
                    **dedup_keys,
                )
                self.db.add(prospect)
                await self.db.flush()

                contact.funnel_prospect_id = prospect.id
                contact.status = "imported"
                contact.imported_at = datetime.utcnow()

                imported += 1
                prospect_ids.append(prospect.id)

            except Exception as e:
                errors.append(f"Fehler bei {contact.name}: {e!s}")
                skipped += 1

        await self.db.flush()

        logger.info(
            "LinkedIn Import: {imported} importiert, {dup} Duplikate, {skip} übersprungen",
            imported=imported,
            dup=duplicates,
            skip=skipped,
        )

        return LinkedInImportResult(
            total=len(contacts),
            imported=imported,
            skipped=skipped,
            duplicates=duplicates,
            companies_created=companies_created,
            errors=errors[:10],
            prospect_ids=prospect_ids,
        )

    async def delete_contact(self, tenant_id: str, contact_id: int) -> None:
        """Delete a single LinkedIn contact."""
        contact = await self.get_by_id(tenant_id, contact_id)
        await self.db.delete(contact)
        await self.db.commit()

    async def delete_contacts_bulk(
        self, tenant_id: str, contact_ids: list[int]
    ) -> int:
        """Delete multiple LinkedIn contacts.

        Returns:
            Number of contacts deleted.
        """
        result = await self.db.execute(
            select(LinkedInContact).where(
                LinkedInContact.tenant_id == tenant_id,
                LinkedInContact.id.in_(contact_ids),
            )
        )
        contacts = list(result.scalars().all())
        for contact in contacts:
            await self.db.delete(contact)
        await self.db.commit()
        return len(contacts)

    async def delete_contacts_by_job(
        self, tenant_id: str, job_id: int
    ) -> int:
        """Delete all contacts for a specific job.

        Returns:
            Number of contacts deleted.
        """
        result = await self.db.execute(
            select(LinkedInContact).where(
                LinkedInContact.tenant_id == tenant_id,
                LinkedInContact.scraper_job_id == job_id,
            )
        )
        contacts = list(result.scalars().all())
        for contact in contacts:
            await self.db.delete(contact)
        await self.db.commit()
        return len(contacts)


class LinkedInStatsService:
    """Service for LinkedIn statistics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_stats(self, tenant_id: str) -> dict:
        """Get overall LinkedIn statistics."""
        # Accounts
        accounts_total = await self.db.execute(
            select(func.count(LinkedInAccount.id)).where(
                LinkedInAccount.tenant_id == tenant_id
            )
        )
        accounts_active = await self.db.execute(
            select(func.count(LinkedInAccount.id)).where(
                LinkedInAccount.tenant_id == tenant_id,
                LinkedInAccount.status == "active",
            )
        )

        # Jobs
        jobs_total = await self.db.execute(
            select(func.count(LinkedInScraperJob.id)).where(
                LinkedInScraperJob.tenant_id == tenant_id
            )
        )
        jobs_running = await self.db.execute(
            select(func.count(LinkedInScraperJob.id)).where(
                LinkedInScraperJob.tenant_id == tenant_id,
                LinkedInScraperJob.status == "running",
            )
        )
        jobs_completed = await self.db.execute(
            select(func.count(LinkedInScraperJob.id)).where(
                LinkedInScraperJob.tenant_id == tenant_id,
                LinkedInScraperJob.status == "completed",
            )
        )

        # Contacts
        contacts_scraped = await self.db.execute(
            select(func.count(LinkedInContact.id)).where(
                LinkedInContact.tenant_id == tenant_id
            )
        )
        contacts_imported = await self.db.execute(
            select(func.count(LinkedInContact.id)).where(
                LinkedInContact.tenant_id == tenant_id,
                LinkedInContact.status == "imported",
            )
        )

        # Today's activity
        profiles_today = await self.db.execute(
            select(func.sum(LinkedInAccount.profiles_scraped_today)).where(
                LinkedInAccount.tenant_id == tenant_id
            )
        )

        # Remaining daily limit
        remaining = await self.db.execute(
            select(
                func.sum(LinkedInAccount.daily_profile_limit)
                - func.sum(LinkedInAccount.profiles_scraped_today)
            ).where(
                LinkedInAccount.tenant_id == tenant_id,
                LinkedInAccount.status == "active",
            )
        )

        return {
            "accounts_total": accounts_total.scalar() or 0,
            "accounts_active": accounts_active.scalar() or 0,
            "jobs_total": jobs_total.scalar() or 0,
            "jobs_running": jobs_running.scalar() or 0,
            "jobs_completed": jobs_completed.scalar() or 0,
            "contacts_scraped": contacts_scraped.scalar() or 0,
            "contacts_imported": contacts_imported.scalar() or 0,
            "profiles_today": profiles_today.scalar() or 0,
            "daily_limit_remaining": remaining.scalar() or 0,
        }
