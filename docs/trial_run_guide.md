# Trial Run Guide — Accounting Team

This guide explains what trial mode is, how to read the daily report,
and how to approve transactions for Epic posting.

---

## What is Trial Mode?

Trial mode lets you see **exactly what the system would post to Applied Epic**
before anything actually gets written.

In trial mode:
- ✅ All carrier statements are parsed and processed
- ✅ All transactions are validated against your data lake
- ✅ You receive a full daily report
- ❌ **Nothing is written to Applied Epic**

This gives you 2+ weeks to verify accuracy before enabling live posting.

---

## Reading the Daily Dashboard

Open the dashboard at: `http://localhost:8501`

### Top Row — Today's Scorecard

| Metric | What It Means |
|---|---|
| **Total Transactions** | All transactions parsed from today's carrier statements |
| **Auto-Approved** | Transactions ≥95% confidence — system is sure these are correct |
| **Review Queue** | Transactions 80–94% confidence — need your eyes before posting |
| **Posted to Epic** | Entries actually written to Applied Epic (0 in trial mode) |
| **Avg Confidence** | Overall system confidence for today's batch |

### What's a Good Result?

In the first week, you might see:
- Auto-approval rate: 70–85% (normal while system learns carrier formats)
- Review queue: 15–25%

By week 2, you should see:
- Auto-approval rate: 90%+
- Review queue: <10%

---

## Reviewing the Exception Queue

The exception queue shows transactions that need your review.
Click any row to see:
- The original line from the carrier statement
- What the system parsed it as
- Why the confidence score is lower than 95%
- The specific warnings or errors

### Common Exception Reasons

| Reason | What to Do |
|---|---|
| "Policy not found in Epic" | Check if policy number format differs from Epic. If it's a real policy, note the correct Epic policy number and provide to the tech team. |
| "Client name mismatch" | Verify the client is the same account — sometimes DBA names differ. If correct, approve with a note. |
| "Amount differs significantly from Epic premium" | Check if this is an endorsement, partial period, or return premium. If correct, approve with explanation. |
| "Duplicate detected" | System found an identical transaction already in Epic. Reject if truly duplicate. |

### Approving a Transaction

1. Click the transaction in the exception queue
2. Review the source data vs. what was parsed
3. If correct: enter your name, click **Approve**
4. If wrong: enter your name, enter the reason, click **Reject**

### Bulk Approval (After Verifying a Full Run)

If you've reviewed a carrier's full run and it looks correct:
1. Copy the **Run ID** from the run (shown in the dashboard)
2. Enter it in the "Bulk Actions" section
3. Click **Approve Entire Run**

---

## Daily Checklist (Trial Phase)

Every morning during the trial period:

- [ ] Open the dashboard
- [ ] Check today's auto-approval rate — is it trending up?
- [ ] Review the exception queue — any systematic errors?
- [ ] Note any new exception patterns (bring to tech team meeting)
- [ ] Compare spot-check of 5 transactions against the original carrier statements
- [ ] Sign off in the reviewer field

---

## Promoting to Live Mode

We'll move to live mode (actual Epic posting) when:
1. Auto-approval rate ≥ 90% for 2 consecutive weeks
2. All reviewed exceptions were correct (system made the right call, just lower confidence)
3. No systematic mismatches with Epic
4. Accounting team lead signs off

The switch is per-carrier — we can go live with Nationwide while Travelers stays in trial.

---

## Questions?

Contact the data analytics team or create a ticket.
DO NOT manually correct things in Epic that you think the system got wrong — 
document them in the review notes so we can improve the matching logic.
