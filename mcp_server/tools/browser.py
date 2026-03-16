"""
Browser automation tools — download carrier statements from carrier portals.
Uses Playwright to log in, navigate, and download PDF/Excel files.
"""

import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
import structlog

from mcp_server.config import Config
from mcp_server.schemas.carrier_schemas import get_carrier_schema

log = structlog.get_logger(__name__)

DOWNLOAD_DIR = Path("downloads")


async def browse_carrier_portal(
    carrier: str,
    username: str,
    password: str,
    mode: str = "trial",
    download_dir: Optional[str] = None,
) -> dict:
    """
    Log into a carrier portal and download the latest statement(s).
    Returns paths to downloaded files for ingestion.

    Args:
        carrier: Carrier slug
        username: Portal login username
        password: Portal login password
        mode: 'trial' or 'live'
        download_dir: Optional override for download directory
    """
    from playwright.async_api import async_playwright

    schema = get_carrier_schema(carrier)
    if not schema.portal_url:
        return {
            "carrier": carrier,
            "status": "error",
            "message": f"No portal URL configured for carrier '{carrier}'. "
                       f"Add portal_url to carrier_configs/{carrier}.yaml",
        }

    target_dir = Path(download_dir) if download_dir else DOWNLOAD_DIR / carrier
    target_dir.mkdir(parents=True, exist_ok=True)

    run_id = str(uuid.uuid4())
    downloaded_files = []

    log.info("Starting portal download",
             carrier=carrier, portal=schema.portal_url, run_id=run_id)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            # Navigate to portal
            await page.goto(schema.portal_url, wait_until="networkidle")

            # Login
            if schema.portal_login_selector:
                await page.fill('input[type="text"], input[name="username"]', username)
                await page.fill('input[type="password"]', password)
                await page.click(schema.portal_login_selector)
                await page.wait_for_load_state("networkidle")

            # Download statement
            if schema.portal_download_selector:
                async with page.expect_download() as download_info:
                    await page.click(schema.portal_download_selector)
                download = await download_info.value
                dest = str(target_dir / download.suggested_filename)
                await download.save_as(dest)
                downloaded_files.append(dest)

            log.info("Portal download complete",
                     carrier=carrier, files=len(downloaded_files))

        except Exception as e:
            log.error("Portal download failed", carrier=carrier, error=str(e))
            return {
                "carrier": carrier,
                "run_id": run_id,
                "status": "error",
                "message": str(e),
            }
        finally:
            await browser.close()

    return {
        "carrier": carrier,
        "run_id": run_id,
        "status": "success",
        "downloaded_files": downloaded_files,
        "download_dir": str(target_dir),
        "downloaded_at": datetime.utcnow().isoformat(),
    }
