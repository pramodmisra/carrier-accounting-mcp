"""
Confidence scoring logic.
Scores each transaction 0.0–1.0 based on how confident we are in the data.
Factors: policy match, amount match, client name match, date validity, duplicates.
"""

from decimal import Decimal
from typing import Optional
from mcp_server.schemas.canonical import CanonicalTransaction
from mcp_server.config import Config


class ConfidenceScorer:

    AUTO_POST_THRESHOLD = Config.AUTO_POST_THRESHOLD    # default 0.95
    REVIEW_THRESHOLD = Config.REVIEW_THRESHOLD          # default 0.80

    def score(
        self,
        transaction: CanonicalTransaction,
        bq_match: Optional[dict],
        is_duplicate: bool,
    ) -> CanonicalTransaction:
        """
        Score a transaction and update its confidence_score, confidence_factors,
        validation_warnings, and validation_errors in-place. Returns the transaction.
        """
        factors = {}
        warnings = []
        errors = []

        # ---- 1. Policy Match (40 pts) ----
        if bq_match:
            factors["policy_match"] = 1.0
            transaction.epic_policy_id = bq_match["epic_policy_id"]
            transaction.epic_client_id = bq_match["epic_client_id"]
        else:
            factors["policy_match"] = 0.0
            errors.append(f"Policy '{transaction.policy_number}' not found in Epic for carrier '{transaction.carrier}'")

        # ---- 2. Client Name Match (20 pts) ----
        if bq_match and transaction.client_name:
            similarity = self._name_similarity(
                transaction.client_name,
                bq_match.get("client_name", "")
            )
            factors["client_name_match"] = similarity
            if similarity < 0.7:
                warnings.append(
                    f"Client name mismatch: statement='{transaction.client_name}' "
                    f"vs Epic='{bq_match.get('client_name')}' (similarity={similarity:.2f})"
                )
        else:
            factors["client_name_match"] = 0.5  # Can't verify, partial credit

        # ---- 3. Amount Reasonableness (20 pts) ----
        if bq_match and bq_match.get("best_billed_premium"):
            epic_premium = Decimal(str(bq_match["best_billed_premium"]))
            if epic_premium > 0:
                ratio = abs(transaction.amount) / epic_premium
                if 0.5 <= ratio <= 2.0:
                    factors["amount_reasonable"] = 1.0
                elif 0.2 <= ratio <= 5.0:
                    factors["amount_reasonable"] = 0.6
                    warnings.append(f"Amount ${transaction.amount} is unusual vs Epic premium ${epic_premium}")
                else:
                    factors["amount_reasonable"] = 0.2
                    warnings.append(f"Amount ${transaction.amount} significantly differs from Epic premium ${epic_premium}")
            else:
                factors["amount_reasonable"] = 0.8
        else:
            factors["amount_reasonable"] = 0.7  # No reference to compare

        # ---- 4. Date Validity (10 pts) ----
        if transaction.effective_date:
            from datetime import date
            today = date.today()
            years_diff = abs((today - transaction.effective_date).days) / 365
            if years_diff <= 2:
                factors["date_valid"] = 1.0
            elif years_diff <= 5:
                factors["date_valid"] = 0.6
                warnings.append(f"Effective date {transaction.effective_date} is >2 years from today")
            else:
                factors["date_valid"] = 0.2
                errors.append(f"Effective date {transaction.effective_date} is >5 years from today")
        else:
            factors["date_valid"] = 0.3
            warnings.append("No effective date found")

        # ---- 5. Duplicate Check (10 pts) ----
        if is_duplicate:
            factors["not_duplicate"] = 0.0
            errors.append("Duplicate transaction detected — identical entry already in Epic")
        else:
            factors["not_duplicate"] = 1.0

        # ---- Weighted Score ----
        weights = {
            "policy_match": 0.40,
            "client_name_match": 0.20,
            "amount_reasonable": 0.20,
            "date_valid": 0.10,
            "not_duplicate": 0.10,
        }
        score = sum(factors[k] * weights[k] for k in weights)

        # Hard block: duplicate or no policy match → score cap
        if is_duplicate:
            score = min(score, 0.20)
        if not bq_match:
            score = min(score, 0.60)

        transaction.confidence_score = round(score, 4)
        transaction.confidence_factors = factors
        transaction.validation_warnings = warnings
        transaction.validation_errors = errors

        return transaction

    def classify(self, transaction: CanonicalTransaction) -> str:
        """Return 'auto', 'review', or 'reject' based on score."""
        if transaction.confidence_score >= self.AUTO_POST_THRESHOLD:
            return "auto"
        elif transaction.confidence_score >= self.REVIEW_THRESHOLD:
            return "review"
        else:
            return "reject"

    @staticmethod
    def _name_similarity(a: str, b: str) -> float:
        """Simple token overlap similarity for client name matching."""
        if not a or not b:
            return 0.0
        a_tokens = set(a.lower().split())
        b_tokens = set(b.lower().split())
        # Remove common noise words
        noise = {"inc", "llc", "ltd", "corp", "the", "and", "&", "co", "of"}
        a_tokens -= noise
        b_tokens -= noise
        if not a_tokens or not b_tokens:
            return 0.5
        intersection = a_tokens & b_tokens
        union = a_tokens | b_tokens
        return len(intersection) / len(union)
