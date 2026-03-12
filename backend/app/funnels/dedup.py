"""Deduplication service for funnel prospects."""

import re
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.models import Contact
from app.funnels.models import FunnelProspect
from app.funnels.schemas import DuplicateCheckResponse, DuplicateMatch


def normalize_email(email: str | None) -> str | None:
    """Normalize email for deduplication.

    - Lowercase
    - Remove + aliases (everything after + before @)
    - Remove dots in Gmail addresses (they're ignored by Gmail)
    """
    if not email:
        return None

    email = email.lower().strip()

    # Split local part and domain
    if "@" not in email:
        return email

    local, domain = email.rsplit("@", 1)

    # Remove + alias
    if "+" in local:
        local = local.split("+")[0]

    # Remove dots for gmail/googlemail
    if domain in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")

    return f"{local}@{domain}"


def normalize_linkedin(linkedin_url: str | None) -> str | None:
    """Normalize LinkedIn URL to profile ID.

    Extracts the profile ID from URLs like:
    - https://www.linkedin.com/in/username
    - https://linkedin.com/in/username/
    - linkedin.com/in/username
    """
    if not linkedin_url:
        return None

    url = linkedin_url.lower().strip()

    # Handle URLs without protocol
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        parsed = urlparse(url)

        # Check if it's a LinkedIn URL
        if "linkedin.com" not in parsed.netloc:
            return None

        # Extract path and find profile ID
        path = parsed.path.strip("/")
        parts = path.split("/")

        # Look for /in/username pattern
        if "in" in parts:
            idx = parts.index("in")
            if idx + 1 < len(parts):
                profile_id = parts[idx + 1]
                # Remove any query params or fragments that might be attached
                profile_id = profile_id.split("?")[0]
                return profile_id

        return None
    except Exception:
        return None


def normalize_phone(phone: str | None) -> str | None:
    """Normalize phone number for deduplication.

    - Keep only digits
    - Take last 10 digits (assuming national format)
    """
    if not phone:
        return None

    # Remove all non-digits
    digits = re.sub(r"\D", "", phone)

    if not digits:
        return None

    # Take last 10 digits for comparison
    if len(digits) > 10:
        digits = digits[-10:]

    return digits


def normalize_domain(domain: str | None) -> str | None:
    """Normalize domain for deduplication.

    - Lowercase
    - Remove www. prefix
    - Remove protocol
    """
    if not domain:
        return None

    domain = domain.lower().strip()

    # Remove protocol if present
    if domain.startswith(("http://", "https://")):
        try:
            parsed = urlparse(domain)
            domain = parsed.netloc
        except Exception:
            pass

    # Remove www. prefix
    if domain.startswith("www."):
        domain = domain[4:]

    return domain


class DeduplicationService:
    """Service for checking and handling duplicates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_duplicates(
        self,
        tenant_id: str,
        email: str | None = None,
        linkedin_url: str | None = None,
        phone: str | None = None,
        exclude_prospect_id: int | None = None,
        exclude_funnel_id: int | None = None,
    ) -> DuplicateCheckResponse:
        """Check for duplicates across funnels and CRM contacts."""
        matches: list[DuplicateMatch] = []

        # Normalize inputs
        norm_email = normalize_email(email)
        norm_linkedin = normalize_linkedin(linkedin_url)
        norm_phone = normalize_phone(phone)

        # Check funnel prospects
        if norm_email:
            funnel_matches = await self._check_funnel_email(
                tenant_id, norm_email, exclude_prospect_id, exclude_funnel_id
            )
            matches.extend(funnel_matches)

        if norm_linkedin:
            funnel_matches = await self._check_funnel_linkedin(
                tenant_id, norm_linkedin, exclude_prospect_id, exclude_funnel_id
            )
            matches.extend(funnel_matches)

        if norm_phone:
            funnel_matches = await self._check_funnel_phone(
                tenant_id, norm_phone, exclude_prospect_id, exclude_funnel_id
            )
            matches.extend(funnel_matches)

        # Check CRM contacts
        if norm_email:
            crm_matches = await self._check_crm_email(tenant_id, email)  # CRM uses original
            matches.extend(crm_matches)

        if norm_linkedin:
            crm_matches = await self._check_crm_linkedin(tenant_id, linkedin_url)
            matches.extend(crm_matches)

        # Deduplicate matches (same entity might match on multiple fields)
        unique_matches = self._deduplicate_matches(matches)

        return DuplicateCheckResponse(
            has_duplicates=len(unique_matches) > 0,
            matches=unique_matches,
        )

    async def _check_funnel_email(
        self,
        tenant_id: str,
        dedup_email: str,
        exclude_id: int | None,
        exclude_funnel_id: int | None,
    ) -> list[DuplicateMatch]:
        """Check for email duplicates in funnel prospects."""
        from app.funnels.models import Funnel

        query = (
            select(FunnelProspect, Funnel.name.label("funnel_name"))
            .join(Funnel)
            .where(
                FunnelProspect.tenant_id == tenant_id,
                FunnelProspect.dedup_email == dedup_email,
            )
        )

        if exclude_id:
            query = query.where(FunnelProspect.id != exclude_id)
        if exclude_funnel_id:
            query = query.where(FunnelProspect.funnel_id != exclude_funnel_id)

        result = await self.db.execute(query)
        rows = result.all()

        matches = []
        for prospect, funnel_name in rows:
            matches.append(
                DuplicateMatch(
                    match_type="funnel_prospect",
                    match_field="email",
                    confidence=1.0,
                    prospect_id=prospect.id,
                    prospect_name=prospect.name,
                    prospect_funnel_id=prospect.funnel_id,
                    prospect_funnel_name=funnel_name,
                )
            )

        return matches

    async def _check_funnel_linkedin(
        self,
        tenant_id: str,
        dedup_linkedin: str,
        exclude_id: int | None,
        exclude_funnel_id: int | None,
    ) -> list[DuplicateMatch]:
        """Check for LinkedIn duplicates in funnel prospects."""
        from app.funnels.models import Funnel

        query = (
            select(FunnelProspect, Funnel.name.label("funnel_name"))
            .join(Funnel)
            .where(
                FunnelProspect.tenant_id == tenant_id,
                FunnelProspect.dedup_linkedin == dedup_linkedin,
            )
        )

        if exclude_id:
            query = query.where(FunnelProspect.id != exclude_id)
        if exclude_funnel_id:
            query = query.where(FunnelProspect.funnel_id != exclude_funnel_id)

        result = await self.db.execute(query)
        rows = result.all()

        matches = []
        for prospect, funnel_name in rows:
            matches.append(
                DuplicateMatch(
                    match_type="funnel_prospect",
                    match_field="linkedin",
                    confidence=1.0,
                    prospect_id=prospect.id,
                    prospect_name=prospect.name,
                    prospect_funnel_id=prospect.funnel_id,
                    prospect_funnel_name=funnel_name,
                )
            )

        return matches

    async def _check_funnel_phone(
        self,
        tenant_id: str,
        dedup_phone: str,
        exclude_id: int | None,
        exclude_funnel_id: int | None,
    ) -> list[DuplicateMatch]:
        """Check for phone duplicates in funnel prospects."""
        from app.funnels.models import Funnel

        query = (
            select(FunnelProspect, Funnel.name.label("funnel_name"))
            .join(Funnel)
            .where(
                FunnelProspect.tenant_id == tenant_id,
                FunnelProspect.dedup_phone == dedup_phone,
            )
        )

        if exclude_id:
            query = query.where(FunnelProspect.id != exclude_id)
        if exclude_funnel_id:
            query = query.where(FunnelProspect.funnel_id != exclude_funnel_id)

        result = await self.db.execute(query)
        rows = result.all()

        matches = []
        for prospect, funnel_name in rows:
            matches.append(
                DuplicateMatch(
                    match_type="funnel_prospect",
                    match_field="phone",
                    confidence=0.9,  # Phone is less reliable
                    prospect_id=prospect.id,
                    prospect_name=prospect.name,
                    prospect_funnel_id=prospect.funnel_id,
                    prospect_funnel_name=funnel_name,
                )
            )

        return matches

    async def _check_crm_email(
        self, tenant_id: str, email: str | None
    ) -> list[DuplicateMatch]:
        """Check for email duplicates in CRM contacts."""
        if not email:
            return []

        # CRM contact uses plain email (with unique constraint)
        query = select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.email == email.lower(),
        )

        result = await self.db.execute(query)
        contacts = result.scalars().all()

        matches = []
        for contact in contacts:
            matches.append(
                DuplicateMatch(
                    match_type="crm_contact",
                    match_field="email",
                    confidence=1.0,
                    contact_id=contact.id,
                    contact_name=contact.name,
                    contact_email=contact.email,
                )
            )

        return matches

    async def _check_crm_linkedin(
        self, tenant_id: str, linkedin_url: str | None
    ) -> list[DuplicateMatch]:
        """Check for LinkedIn duplicates in CRM contacts."""
        if not linkedin_url:
            return []

        # CRM contact stores linkedin URL, search for partial match
        norm_linkedin = normalize_linkedin(linkedin_url)
        if not norm_linkedin:
            return []

        query = select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.linkedin.ilike(f"%{norm_linkedin}%"),
        )

        result = await self.db.execute(query)
        contacts = result.scalars().all()

        matches = []
        for contact in contacts:
            matches.append(
                DuplicateMatch(
                    match_type="crm_contact",
                    match_field="linkedin",
                    confidence=0.95,
                    contact_id=contact.id,
                    contact_name=contact.name,
                    contact_email=contact.email,
                )
            )

        return matches

    def _deduplicate_matches(self, matches: list[DuplicateMatch]) -> list[DuplicateMatch]:
        """Remove duplicate matches for the same entity."""
        seen = set()
        unique = []

        for match in matches:
            # Create a key for uniqueness
            if match.match_type == "funnel_prospect":
                key = f"funnel_{match.prospect_id}"
            else:
                key = f"crm_{match.contact_id}"

            if key not in seen:
                seen.add(key)
                unique.append(match)

        return unique


def compute_dedup_keys(
    email: str | None = None,
    linkedin_url: str | None = None,
    phone: str | None = None,
) -> dict[str, str | None]:
    """Compute all dedup keys for a prospect."""
    return {
        "dedup_email": normalize_email(email),
        "dedup_linkedin": normalize_linkedin(linkedin_url),
        "dedup_phone": normalize_phone(phone),
    }


def compute_company_dedup_key(domain: str | None) -> str | None:
    """Compute dedup key for a company based on domain."""
    return normalize_domain(domain)
