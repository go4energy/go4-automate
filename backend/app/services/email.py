"""Email service - SMTP-based email sending with tenant branding."""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from loguru import logger

from app.config import settings
from app.exceptions import ExternalServiceError


class EmailService:
    """Send branded emails via SMTP."""

    def __init__(self, tenant_config: dict | None = None) -> None:
        self.tenant_config = tenant_config or {}

    def _load_template(self, category: str, filename: str) -> str:
        """Load HTML template from config/templates/."""
        template_path = Path(settings.template_dir) / category / filename
        if not template_path.exists():
            raise ExternalServiceError(
                "Email-Template", f"Template nicht gefunden: {template_path}"
            )
        return template_path.read_text(encoding="utf-8")

    def _render_template(self, html: str, variables: dict) -> str:
        """Replace {{variable}} placeholders in template."""
        for key, value in variables.items():
            html = html.replace(f"{{{{{key}}}}}", str(value))
        return html

    def _build_variables(self, extra: dict | None = None) -> dict:
        """Build template variables from tenant config."""
        variables = {
            "company_name": self.tenant_config.get("COMPANY_NAME", ""),
            "brand_color": self.tenant_config.get("BRAND_COLOR", "#FF6600"),
            "website_url": self.tenant_config.get("WEBSITE_URL", ""),
            "contact_email": self.tenant_config.get("CONTACT_EMAIL", ""),
            "contact_phone": self.tenant_config.get("CONTACT_PHONE", ""),
            "logo_url": self.tenant_config.get("BRAND_LOGO_URL", ""),
        }
        if extra:
            variables.update(extra)
        return variables

    async def send(
        self,
        to_email: str,
        subject: str,
        template_category: str,
        template_file: str,
        extra_variables: dict | None = None,
    ) -> bool:
        """Send a branded email using a template."""
        if not settings.smtp_host:
            logger.warning("SMTP nicht konfiguriert - E-Mail wird übersprungen")
            return False

        html_template = self._load_template(template_category, template_file)
        variables = self._build_variables(extra_variables)
        html_body = self._render_template(html_template, variables)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        try:
            await asyncio.get_event_loop().run_in_executor(None, self._send_smtp, msg)
            logger.info("E-Mail gesendet an {to}", to=to_email)
            return True
        except Exception as e:
            logger.error("E-Mail-Fehler an {to}: {err}", to=to_email, err=str(e))
            raise ExternalServiceError("SMTP", str(e)) from e

    def _send_smtp(self, msg: MIMEMultipart) -> None:
        """Synchronous SMTP send (runs in executor)."""
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
