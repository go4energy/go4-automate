"""Email tracking utilities - link rewriting, open pixel, unsubscribe."""

import base64
import re

from loguru import logger

# 1x1 transparent GIF
TRACKING_PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


def generate_tracking_pixel() -> bytes:
    """Return a 1x1 transparent GIF for open tracking."""
    return TRACKING_PIXEL


def encode_url(url: str) -> str:
    """Base64 encode a URL for tracking redirect."""
    return base64.urlsafe_b64encode(url.encode()).decode()


def decode_url(encoded: str) -> str:
    """Decode a base64 encoded URL."""
    try:
        # Add padding if needed
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += "=" * padding
        return base64.urlsafe_b64decode(encoded).decode()
    except Exception as e:
        logger.error("URL decode fehlgeschlagen: {err}", err=str(e))
        return ""


def rewrite_links(
    html_content: str,
    tracking_token: str,
    base_tracking_url: str,
) -> str:
    """Rewrite all links in HTML content for click tracking.

    Args:
        html_content: The HTML email content.
        tracking_token: Unique token for this recipient.
        base_tracking_url: Base URL for tracking (e.g., https://api.go4.energy).

    Returns:
        HTML with rewritten links pointing to tracking endpoint.

    Example:
        Original:  href="https://example.com/page"
        Rewritten: href="https://api.go4.energy/t/c/{token}/aHR0cHM6Ly9leGFtcGxlLmNvbS9wYWdl"
    """
    # Pattern to match href attributes
    href_pattern = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)

    def replace_link(match: re.Match) -> str:
        original_url = match.group(1)

        # Skip special URLs
        if original_url.startswith(("#", "mailto:", "tel:", "javascript:")):
            return match.group(0)

        # Skip unsubscribe links (keep them direct)
        if "unsubscribe" in original_url.lower():
            return match.group(0)

        # Encode the original URL
        encoded = encode_url(original_url)

        # Build tracking URL
        tracking_url = f"{base_tracking_url.rstrip('/')}/t/c/{tracking_token}/{encoded}"

        return f'href="{tracking_url}"'

    return href_pattern.sub(replace_link, html_content)


def add_open_tracking_pixel(
    html_content: str,
    tracking_token: str,
    base_tracking_url: str,
) -> str:
    """Add open tracking pixel to HTML content.

    Args:
        html_content: The HTML email content.
        tracking_token: Unique token for this recipient.
        base_tracking_url: Base URL for tracking.

    Returns:
        HTML with tracking pixel added before </body> or at the end.
    """
    pixel_url = f"{base_tracking_url.rstrip('/')}/t/o/{tracking_token}.gif"
    pixel_html = f'<img src="{pixel_url}" width="1" height="1" alt="" style="display:none;width:1px;height:1px;" />'

    # Try to insert before </body>
    if "</body>" in html_content.lower():
        # Case-insensitive replacement
        pattern = re.compile(r"(</body>)", re.IGNORECASE)
        return pattern.sub(f"{pixel_html}\\1", html_content)

    # If no body tag, append at the end
    return html_content + pixel_html


def add_unsubscribe_link(
    html_content: str,
    tracking_token: str,
    base_tracking_url: str,
) -> str:
    """Add unsubscribe link placeholder to HTML if not present.

    The template should include {{unsubscribe_url}} placeholder.
    This function replaces it with the actual URL.

    Args:
        html_content: The HTML email content.
        tracking_token: Unique token for this recipient.
        base_tracking_url: Base URL for tracking.

    Returns:
        HTML with unsubscribe URL injected.
    """
    unsubscribe_url = f"{base_tracking_url.rstrip('/')}/t/u/{tracking_token}"

    # Replace placeholder
    return html_content.replace("{{unsubscribe_url}}", unsubscribe_url)


def process_email_content(
    html_content: str,
    tracking_token: str,
    base_tracking_url: str,
    merge_data: dict | None = None,
) -> str:
    """Process email content with all tracking features.

    Args:
        html_content: Raw HTML template content.
        tracking_token: Unique token for this recipient.
        base_tracking_url: Base URL for tracking endpoints.
        merge_data: Dictionary of merge tag values.

    Returns:
        Fully processed HTML ready for sending.
    """
    # 1. Replace merge tags
    if merge_data:
        html_content = replace_merge_tags(html_content, merge_data)

    # 2. Add unsubscribe link
    html_content = add_unsubscribe_link(html_content, tracking_token, base_tracking_url)

    # 3. Rewrite links for click tracking
    html_content = rewrite_links(html_content, tracking_token, base_tracking_url)

    # 4. Add open tracking pixel
    html_content = add_open_tracking_pixel(
        html_content, tracking_token, base_tracking_url
    )

    return html_content


def replace_merge_tags(content: str, data: dict) -> str:
    """Replace merge tags in content with actual values.

    Supports formats:
    - {{name}}
    - {{contact.name}}
    - {{company}}

    Args:
        content: HTML or text content with merge tags.
        data: Dictionary of values to replace.

    Returns:
        Content with merge tags replaced.
    """
    # Pattern for {{tag}} or {{object.property}}
    pattern = re.compile(r"\{\{(\w+(?:\.\w+)?)\}\}")

    def replace_tag(match: re.Match) -> str:
        tag = match.group(1)

        # Handle nested keys like "contact.name"
        if "." in tag:
            parts = tag.split(".")
            value = data
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, "")
                else:
                    value = ""
                    break
            return str(value) if value else ""

        # Simple key lookup
        return str(data.get(tag, ""))

    return pattern.sub(replace_tag, content)


def extract_merge_tags(content: str) -> list[str]:
    """Extract all merge tags from content.

    Args:
        content: HTML or text content with merge tags.

    Returns:
        List of unique merge tag names.
    """
    pattern = re.compile(r"\{\{(\w+(?:\.\w+)?)\}\}")
    tags = pattern.findall(content)
    return list(set(tags))
