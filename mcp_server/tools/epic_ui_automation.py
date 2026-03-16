"""
Gap #7: Applied Epic UI automation via Playwright.
Fallback write path when the REST API / SDK is unavailable.
Automates the Epic web UI to enter accounting transactions.
"""

import uuid
from datetime import datetime
from typing import Optional
import structlog

from mcp_server.config import Config
from mcp_server.schemas.canonical import CanonicalTransaction, TransactionStatus
from mcp_server.services.bigquery_client import BigQueryClient

log = structlog.get_logger(__name__)

bq = BigQueryClient()

# Epic web UI selectors — adjust to match your agency's Epic web interface
EPIC_UI_CONFIG = {
    "login_url": Config.EPIC_SDK_URL.replace("/api/v1", "") if Config.EPIC_SDK_URL else "https://epic.appliedsystems.com",
    "username_selector": 'input[name="username"], input[id="username"]',
    "password_selector": 'input[name="password"], input[type="password"]',
    "login_button_selector": 'button[type="submit"], input[type="submit"]',
    # Accounting entry form selectors
    "accounting_menu_selector": 'a[href*="accounting"], [data-menu="accounting"]',
    "new_entry_selector": 'button:has-text("New Entry"), a:has-text("New Entry")',
    "policy_search_selector": 'input[name="policySearch"], input[id="policySearch"]',
    "policy_select_selector": '.search-result:first-child, tr.policy-row:first-child',
    "transaction_type_selector": 'select[name="transactionType"], select[id="transactionType"]',
    "amount_selector": 'input[name="amount"], input[id="amount"]',
    "effective_date_selector": 'input[name="effectiveDate"], input[id="effectiveDate"]',
    "description_selector": 'input[name="description"], textarea[name="description"]',
    "save_button_selector": 'button:has-text("Save"), button[type="submit"]',
    "confirmation_selector": '.confirmation-message, .success-alert, [class*="success"]',
    "entry_id_selector": '.entry-id, [data-field="entryId"]',
}


async def post_to_epic_via_ui(
    transactions: list[CanonicalTransaction],
    epic_username: str,
    epic_password: str,
    headless: bool = True,
    screenshot_on_error: bool = True,
) -> dict:
    """
    Post accounting entries to Applied Epic by automating the web UI.
    Fallback path when REST API is unavailable.

    Args:
        transactions: Approved transactions to post
        epic_username: Epic web UI login username
        epic_password: Epic web UI login password
        headless: Run browser in headless mode (default True)
        screenshot_on_error: Capture screenshot on failure for debugging

    Returns:
        Posting report with per-transaction results
    """
    from playwright.async_api import async_playwright

    if not transactions:
        return {"status": "empty", "message": "No transactions to post"}

    posted = 0
    failed = 0
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Login to Epic
            log.info("Logging into Applied Epic web UI")
            await page.goto(EPIC_UI_CONFIG["login_url"], wait_until="networkidle")
            await page.fill(EPIC_UI_CONFIG["username_selector"], epic_username)
            await page.fill(EPIC_UI_CONFIG["password_selector"], epic_password)
            await page.click(EPIC_UI_CONFIG["login_button_selector"])
            await page.wait_for_load_state("networkidle")

            # Navigate to accounting
            await page.click(EPIC_UI_CONFIG["accounting_menu_selector"])
            await page.wait_for_load_state("networkidle")

            for txn in transactions:
                try:
                    entry_result = await _enter_single_transaction(page, txn, screenshot_on_error)

                    if entry_result["status"] == "posted":
                        # Update BQ with the entry ID
                        bq.update_transaction_status(
                            transaction_id=txn.transaction_id,
                            status=TransactionStatus.POSTED.value,
                            epic_entry_id=entry_result.get("epic_entry_id"),
                        )
                        posted += 1
                    else:
                        bq.update_transaction_status(
                            transaction_id=txn.transaction_id,
                            status=TransactionStatus.FAILED.value,
                        )
                        failed += 1

                    results.append(entry_result)

                except Exception as e:
                    log.error("UI automation failed for transaction",
                              transaction_id=txn.transaction_id, error=str(e))
                    if screenshot_on_error:
                        screenshot_path = f"screenshots/error_{txn.transaction_id}.png"
                        try:
                            await page.screenshot(path=screenshot_path)
                        except Exception:
                            screenshot_path = None
                    else:
                        screenshot_path = None

                    bq.update_transaction_status(
                        transaction_id=txn.transaction_id,
                        status=TransactionStatus.FAILED.value,
                    )
                    failed += 1
                    results.append({
                        "transaction_id": txn.transaction_id,
                        "status": "failed",
                        "error": str(e),
                        "screenshot": screenshot_path,
                    })

        except Exception as e:
            log.error("Epic UI login/navigation failed", error=str(e))
            return {
                "status": "login_failed",
                "error": str(e),
                "message": "Could not log into Applied Epic web UI. Check credentials and selectors.",
            }
        finally:
            await browser.close()

    log.info("Epic UI automation complete", posted=posted, failed=failed)
    return {
        "method": "ui_automation",
        "posted": posted,
        "failed": failed,
        "total": len(transactions),
        "results": results,
    }


async def _enter_single_transaction(page, txn: CanonicalTransaction, screenshot_on_error: bool) -> dict:
    """Enter a single accounting transaction via the Epic web UI."""

    log.info("Entering transaction via UI",
             transaction_id=txn.transaction_id,
             policy=txn.policy_number,
             amount=str(txn.amount))

    # Click "New Entry"
    await page.click(EPIC_UI_CONFIG["new_entry_selector"])
    await page.wait_for_load_state("networkidle")

    # Search for policy
    policy_search = txn.epic_policy_id or txn.policy_number
    await page.fill(EPIC_UI_CONFIG["policy_search_selector"], policy_search)
    await page.wait_for_timeout(1000)  # Wait for search results

    # Select first matching policy
    try:
        await page.click(EPIC_UI_CONFIG["policy_select_selector"], timeout=5000)
    except Exception:
        return {
            "transaction_id": txn.transaction_id,
            "status": "failed",
            "error": f"Policy not found in Epic UI: {policy_search}",
        }

    await page.wait_for_load_state("networkidle")

    # Fill transaction type
    txn_type_map = {
        "premium": "Premium",
        "commission": "Commission",
        "return_premium": "Return Premium",
        "endorsement": "Endorsement",
        "cancellation": "Cancellation",
        "reinstatement": "Reinstatement",
        "fee": "Fee",
        "adjustment": "Adjustment",
    }
    epic_txn_type = txn_type_map.get(txn.transaction_type.value, "Premium")
    await page.select_option(EPIC_UI_CONFIG["transaction_type_selector"], label=epic_txn_type)

    # Fill amount
    await page.fill(EPIC_UI_CONFIG["amount_selector"], str(txn.amount))

    # Fill effective date
    if txn.effective_date:
        date_str = txn.effective_date.strftime("%m/%d/%Y")
        await page.fill(EPIC_UI_CONFIG["effective_date_selector"], date_str)

    # Fill description
    description = txn.description or f"Carrier statement import - {txn.carrier}"
    description_field = page.locator(EPIC_UI_CONFIG["description_selector"])
    if await description_field.count() > 0:
        await description_field.fill(description)

    # Save
    await page.click(EPIC_UI_CONFIG["save_button_selector"])
    await page.wait_for_load_state("networkidle")

    # Check for confirmation
    epic_entry_id = None
    try:
        confirmation = page.locator(EPIC_UI_CONFIG["confirmation_selector"])
        await confirmation.wait_for(timeout=5000)

        # Try to extract entry ID
        entry_id_el = page.locator(EPIC_UI_CONFIG["entry_id_selector"])
        if await entry_id_el.count() > 0:
            epic_entry_id = await entry_id_el.text_content()
            epic_entry_id = epic_entry_id.strip() if epic_entry_id else None

    except Exception:
        if screenshot_on_error:
            try:
                await page.screenshot(path=f"screenshots/no_confirm_{txn.transaction_id}.png")
            except Exception:
                pass
        return {
            "transaction_id": txn.transaction_id,
            "status": "failed",
            "error": "No confirmation received after save — entry may or may not have been created",
        }

    log.info("Transaction entered via UI",
             transaction_id=txn.transaction_id,
             epic_entry_id=epic_entry_id)

    return {
        "transaction_id": txn.transaction_id,
        "status": "posted",
        "method": "ui_automation",
        "epic_entry_id": epic_entry_id or f"ui_{txn.transaction_id[:8]}",
        "policy_number": txn.policy_number,
        "amount": str(txn.amount),
    }
