"""Unit tests for WebAdapter — bs4 extraction pure-function tests."""

from __future__ import annotations

from app.intel.adapters.web import WebAdapter


def test_extract_strips_scripts_and_styles():
    html = """
    <html><head>
      <title>Test Page</title>
      <meta name="description" content="A test page">
      <style>body{color:red}</style>
      <script>alert('no')</script>
    </head><body>
      <h1>Hello World</h1>
      <p>visible text</p>
      <noscript>hidden</noscript>
    </body></html>
    """
    text, parsed = WebAdapter._extract(html, None)
    assert "alert" not in text
    assert "color:red" not in text
    assert "hidden" not in text
    assert "Hello World" in text
    assert "visible text" in text
    assert parsed["title"] == "Test Page"
    assert parsed["meta_description"] == "A test page"
    assert parsed["h1"] == "Hello World"


def test_extract_with_selector():
    html = (
        "<html><body>"
        "<main><h1>Main</h1><p>main content</p></main>"
        "<aside><p>noise to skip</p></aside>"
        "</body></html>"
    )
    text, _ = WebAdapter._extract(html, "main")
    assert "main content" in text
    assert "noise to skip" not in text


def test_extract_handles_missing_title():
    html = "<html><body><p>just body</p></body></html>"
    text, parsed = WebAdapter._extract(html, None)
    assert "just body" in text
    assert parsed["title"] == ""
    assert parsed["meta_description"] == ""
