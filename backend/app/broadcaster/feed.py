"""RSS 2.0 Feed Generator with iTunes Podcast Namespace."""

import xml.etree.ElementTree as ET
from datetime import datetime

from app.broadcaster.models import BriefingChannel, BriefingEpisode
from app.config import settings

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"


def generate_feed(
    channel: BriefingChannel,
    episodes: list[BriefingEpisode],
    base_url: str,
) -> str:
    """Generate RSS 2.0 XML feed with iTunes Podcast namespace."""
    ET.register_namespace("itunes", ITUNES_NS)

    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:itunes", ITUNES_NS)

    ch = ET.SubElement(rss, "channel")

    # Channel metadata
    ET.SubElement(ch, "title").text = channel.name
    ET.SubElement(ch, "description").text = channel.description or channel.name
    ET.SubElement(ch, "language").text = channel.language or "de"
    ET.SubElement(ch, "link").text = base_url
    ET.SubElement(ch, "generator").text = settings.app_name

    # iTunes tags
    itunes_author = ET.SubElement(ch, f"{{{ITUNES_NS}}}author")
    itunes_author.text = settings.platform_name
    itunes_summary = ET.SubElement(ch, f"{{{ITUNES_NS}}}summary")
    itunes_summary.text = channel.description or channel.name

    if channel.cover_image_url:
        itunes_image = ET.SubElement(ch, f"{{{ITUNES_NS}}}image")
        itunes_image.set("href", channel.cover_image_url)

    itunes_category = ET.SubElement(ch, f"{{{ITUNES_NS}}}category")
    itunes_category.set("text", "Business")

    # Episodes (most recent first)
    for ep in sorted(episodes, key=lambda e: e.episode_number, reverse=True):
        if ep.status != "ready" or not ep.audio_url:
            continue

        item = ET.SubElement(ch, "item")
        ET.SubElement(item, "title").text = ep.title
        ET.SubElement(item, "description").text = ep.summary or ep.title

        # Audio enclosure
        audio_url = ep.audio_url
        if not audio_url.startswith("http"):
            audio_url = f"{base_url}/{audio_url.lstrip('/')}"

        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", audio_url)
        enclosure.set("type", ep.audio_mime_type or "audio/wav")
        enclosure.set("length", str(ep.audio_size_bytes or 0))

        # Timestamps
        pub_date = ep.published_at or ep.created_at
        if pub_date:
            ET.SubElement(item, "pubDate").text = _format_rfc822(pub_date)

        ET.SubElement(item, "guid").text = f"{base_url}/episodes/{ep.id}"

        # iTunes episode tags
        if ep.audio_duration_seconds:
            itunes_dur = ET.SubElement(item, f"{{{ITUNES_NS}}}duration")
            itunes_dur.text = _format_duration(ep.audio_duration_seconds)

        itunes_ep = ET.SubElement(item, f"{{{ITUNES_NS}}}episode")
        itunes_ep.text = str(ep.episode_number)

    return ET.tostring(rss, encoding="unicode", xml_declaration=True)


def _format_rfc822(dt: datetime) -> str:
    """Format datetime as RFC 822 for RSS feeds."""
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def _format_duration(seconds: int) -> str:
    """Format seconds as HH:MM:SS for iTunes duration."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
