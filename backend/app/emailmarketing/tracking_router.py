"""Email tracking router - public endpoints without authentication."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.emailmarketing.service import TrackingService
from app.emailmarketing.tracking import decode_url, generate_tracking_pixel

# Public router - no auth required
# Named 'router' for module discovery compatibility
router = APIRouter(prefix="/emailmarketing/t", tags=["emailmarketing-tracking"])


@router.get("/o/{token}.gif")
async def open_pixel(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Open tracking pixel endpoint.

    Returns a 1x1 transparent GIF and records the open event.
    """
    try:
        # Get client IP
        ip_address = request.client.host if request.client else None

        # Record open event
        service = TrackingService(db)
        await service.record_open(token, ip_address)
        await db.commit()
    except Exception as e:
        logger.error("Open tracking Fehler: {err}", err=str(e))
        # Don't fail the response even if tracking fails

    # Return tracking pixel
    return Response(
        content=generate_tracking_pixel(),
        media_type="image/gif",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/c/{token}/{encoded_url:path}")
async def click_redirect(
    token: str,
    encoded_url: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Click tracking redirect endpoint.

    Decodes the original URL, records the click, and redirects.
    """
    # Decode original URL
    original_url = decode_url(encoded_url)

    if not original_url:
        # Fallback to a safe redirect
        logger.warning("Click tracking: URL decode fehlgeschlagen für {enc}", enc=encoded_url)
        return RedirectResponse(url="/", status_code=302)

    try:
        # Get client info
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Record click event
        service = TrackingService(db)
        await service.record_click(token, original_url, ip_address, user_agent)
        await db.commit()
    except Exception as e:
        logger.error("Click tracking Fehler: {err}", err=str(e))
        # Don't fail the redirect even if tracking fails

    return RedirectResponse(url=original_url, status_code=302)


@router.get("/u/{token}")
async def unsubscribe_page(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Unsubscribe confirmation page."""
    # Simple HTML page for unsubscribe confirmation
    html = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Newsletter abmelden</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 500px;
                margin: 50px auto;
                padding: 20px;
                text-align: center;
            }}
            .container {{
                background: #f9fafb;
                border-radius: 12px;
                padding: 40px;
            }}
            h1 {{
                color: #111827;
                font-size: 24px;
                margin-bottom: 16px;
            }}
            p {{
                color: #6b7280;
                margin-bottom: 24px;
            }}
            button {{
                background: #dc2626;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
            }}
            button:hover {{
                background: #b91c1c;
            }}
            .success {{
                color: #059669;
                display: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Newsletter abmelden</h1>
            <p id="message">Klicken Sie auf den Button, um sich vom Newsletter abzumelden.</p>
            <button id="unsubscribeBtn" onclick="unsubscribe()">Abmelden</button>
            <p id="success" class="success">Sie wurden erfolgreich abgemeldet.</p>
        </div>
        <script>
            async function unsubscribe() {{
                const btn = document.getElementById('unsubscribeBtn');
                const msg = document.getElementById('message');
                const success = document.getElementById('success');

                btn.disabled = true;
                btn.textContent = 'Wird abgemeldet...';

                try {{
                    const response = await fetch('/api/v1/emailmarketing/t/u/{token}/confirm', {{
                        method: 'POST'
                    }});

                    if (response.ok) {{
                        msg.style.display = 'none';
                        btn.style.display = 'none';
                        success.style.display = 'block';
                    }} else {{
                        btn.textContent = 'Fehler - Erneut versuchen';
                        btn.disabled = false;
                    }}
                }} catch (e) {{
                    btn.textContent = 'Fehler - Erneut versuchen';
                    btn.disabled = false;
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.post("/u/{token}/confirm")
async def confirm_unsubscribe(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Process unsubscribe confirmation."""
    try:
        ip_address = request.client.host if request.client else None

        service = TrackingService(db)
        email, tenant_id = await service.record_unsubscribe(token, ip_address)
        await db.commit()

        if email:
            return {"success": True, "email": email}
        else:
            return {"success": False, "error": "Token nicht gefunden"}
    except Exception as e:
        logger.exception("Unsubscribe Fehler")
        return {"success": False, "error": str(e)}
