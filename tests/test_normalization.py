"""Tests for the normalization tools."""

import pytest
from decimal import Decimal

from mcp_server.tools.normalization import (
    _parse_date,
    _parse_decimal,
    _parse_transaction_type,
)
from mcp_server.schemas.canonical import TransactionType


class TestParseDate:
    def test_valid_date(self):
        result = _parse_date("2024-01-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_us_format(self):
        result = _parse_date("01/15/2024")
        assert result is not None
        assert result.month == 1

    def test_none(self):
        assert _parse_date(None) is None

    def test_empty(self):
        assert _parse_date("") is None

    def test_invalid(self):
        assert _parse_date("not-a-date") is None


class TestParseDecimal:
    def test_standard(self):
        assert _parse_decimal("1500.00") == Decimal("1500.00")

    def test_with_commas(self):
        assert _parse_decimal("1,500.00") == Decimal("1500.00")

    def test_with_dollar_sign(self):
        assert _parse_decimal("$1,500.00") == Decimal("1500.00")

    def test_parentheses_negative(self):
        assert _parse_decimal("(500.00)") == Decimal("-500.00")

    def test_none(self):
        assert _parse_decimal(None) == Decimal("0")

    def test_empty(self):
        assert _parse_decimal("") == Decimal("0")

    def test_invalid(self):
        assert _parse_decimal("N/A") == Decimal("0")


class TestParseTransactionType:
    def test_premium(self):
        assert _parse_transaction_type("premium") == TransactionType.PREMIUM

    def test_commission(self):
        assert _parse_transaction_type("commission") == TransactionType.COMMISSION

    def test_return_premium(self):
        assert _parse_transaction_type("return_premium") == TransactionType.RETURN_PREMIUM

    def test_case_insensitive(self):
        assert _parse_transaction_type("PREMIUM") == TransactionType.PREMIUM

    def test_none_defaults_premium(self):
        assert _parse_transaction_type(None) == TransactionType.PREMIUM

    def test_unknown_defaults_premium(self):
        assert _parse_transaction_type("unknown") == TransactionType.PREMIUM
