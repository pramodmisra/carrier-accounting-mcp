"""Tests for the confidence scorer and validation logic."""

import pytest
from decimal import Decimal
from datetime import date

from mcp_server.schemas.canonical import (
    CanonicalTransaction, TransactionStatus, RunMode
)
from mcp_server.services.confidence_scorer import ConfidenceScorer


@pytest.fixture
def scorer():
    return ConfidenceScorer()


@pytest.fixture
def sample_transaction():
    return CanonicalTransaction(
        transaction_id="test-001",
        run_id="run-001",
        source_file="test.pdf",
        carrier="nationwide",
        policy_number="POL-12345",
        client_name="Acme Corporation",
        effective_date=date.today(),
        amount=Decimal("1500.00"),
    )


@pytest.fixture
def bq_match():
    return {
        "epic_policy_id": "EP-001",
        "epic_client_id": "CL-001",
        "client_name": "Acme Corporation",
        "best_billed_premium": Decimal("1500.00"),
        "best_premium": Decimal("1500.00"),
    }


class TestConfidenceScorer:
    def test_perfect_match_scores_high(self, scorer, sample_transaction, bq_match):
        result = scorer.score(sample_transaction, bq_match, is_duplicate=False)
        assert result.confidence_score >= 0.95
        assert result.epic_policy_id == "EP-001"
        assert len(result.validation_errors) == 0

    def test_no_policy_match_caps_score(self, scorer, sample_transaction):
        result = scorer.score(sample_transaction, None, is_duplicate=False)
        assert result.confidence_score <= 0.60
        assert any("not found" in e for e in result.validation_errors)

    def test_duplicate_caps_score(self, scorer, sample_transaction, bq_match):
        result = scorer.score(sample_transaction, bq_match, is_duplicate=True)
        assert result.confidence_score <= 0.20
        assert any("Duplicate" in e for e in result.validation_errors)

    def test_classify_auto(self, scorer, sample_transaction, bq_match):
        scorer.score(sample_transaction, bq_match, is_duplicate=False)
        assert scorer.classify(sample_transaction) == "auto"

    def test_classify_reject_no_match(self, scorer, sample_transaction):
        scorer.score(sample_transaction, None, is_duplicate=False)
        assert scorer.classify(sample_transaction) == "reject"

    def test_name_similarity_exact(self, scorer):
        assert scorer._name_similarity("Acme Corp", "Acme Corp") == 1.0

    def test_name_similarity_partial(self, scorer):
        sim = scorer._name_similarity("Acme Corporation", "Acme Corp Inc")
        assert 0.0 < sim < 1.0

    def test_name_similarity_empty(self, scorer):
        assert scorer._name_similarity("", "Acme") == 0.0

    def test_amount_unusual_warns(self, scorer, sample_transaction, bq_match):
        sample_transaction.amount = Decimal("50000.00")  # Way higher than premium
        result = scorer.score(sample_transaction, bq_match, is_duplicate=False)
        assert any("unusual" in w or "differs" in w for w in result.validation_warnings)


class TestCarrierSchemas:
    def test_registry_has_carriers(self):
        from mcp_server.schemas.carrier_schemas import CARRIER_REGISTRY
        assert "hartford" in CARRIER_REGISTRY
        assert "hanover" in CARRIER_REGISTRY
        assert "principal" in CARRIER_REGISTRY
        assert len(CARRIER_REGISTRY) >= 40

    def test_get_known_carrier(self):
        from mcp_server.schemas.carrier_schemas import get_carrier_schema
        schema = get_carrier_schema("hartford")
        assert schema.carrier_slug == "hartford"
        assert schema.carrier_display_name == "The Hartford"

    def test_get_unknown_carrier_fallback(self):
        from mcp_server.schemas.carrier_schemas import get_carrier_schema
        schema = get_carrier_schema("unknown_carrier")
        assert schema.carrier_slug == "unknown_carrier"
