"""Tests for Epic UI automation (Gap #7)."""

import pytest
from decimal import Decimal
from datetime import date

from mcp_server.schemas.canonical import (
    CanonicalTransaction, TransactionType, TransactionStatus, RunMode
)
from mcp_server.tools.epic_ui_automation import EPIC_UI_CONFIG


class TestEpicUIConfig:
    """Verify UI selectors are properly defined."""

    def test_login_selectors_exist(self):
        assert "login_url" in EPIC_UI_CONFIG
        assert "username_selector" in EPIC_UI_CONFIG
        assert "password_selector" in EPIC_UI_CONFIG
        assert "login_button_selector" in EPIC_UI_CONFIG

    def test_entry_form_selectors_exist(self):
        assert "new_entry_selector" in EPIC_UI_CONFIG
        assert "policy_search_selector" in EPIC_UI_CONFIG
        assert "transaction_type_selector" in EPIC_UI_CONFIG
        assert "amount_selector" in EPIC_UI_CONFIG
        assert "effective_date_selector" in EPIC_UI_CONFIG
        assert "save_button_selector" in EPIC_UI_CONFIG
        assert "confirmation_selector" in EPIC_UI_CONFIG

    def test_all_selectors_are_strings(self):
        for key, value in EPIC_UI_CONFIG.items():
            assert isinstance(value, str), f"Selector '{key}' is not a string"


class TestEpicUIAutomationImport:
    """Verify the module loads without errors."""

    def test_post_function_importable(self):
        from mcp_server.tools.epic_ui_automation import post_to_epic_via_ui
        assert callable(post_to_epic_via_ui)

    def test_enter_transaction_importable(self):
        from mcp_server.tools.epic_ui_automation import _enter_single_transaction
        assert callable(_enter_single_transaction)
