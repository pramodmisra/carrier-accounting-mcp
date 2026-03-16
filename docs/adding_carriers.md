# Adding a New Carrier

This guide walks through onboarding a new carrier into the system end-to-end.
Estimated time: 30–60 minutes per carrier.

---

## Step 1: Collect a Sample Statement

Get at least 3 months of sample statements from the carrier.
Identify the format: PDF or Excel (or both).

Key things to note:
- What columns/fields exist?
- What are the exact column header names?
- What format are dates in? (`MM/DD/YYYY`, `YYYY-MM-DD`, etc.)
- What values appear in the "Transaction Type" field?
- Is there a portal for automated download?

---

## Step 2: Create the Carrier Config File

```bash
cp carrier_configs/carrier_template.yaml carrier_configs/{carrier_slug}.yaml
```

Fill in all field mappings based on the actual column headers in the statement.

Example for a carrier called "Erie":
```yaml
carrier_slug: erie
carrier_display_name: "Erie Insurance"
statement_format: excel
field_mappings:
  policy_number: "Pol #"
  client_name:   "Named Insured"
  premium:       "Gross Premium"
  # ...etc
```

---

## Step 3: Register the Schema in Python

Open `mcp_server/schemas/carrier_schemas/__init__.py` and add:

```python
ERIE = CarrierSchema(
    carrier_slug="erie",
    carrier_display_name="Erie Insurance",
    statement_format="excel",
    policy_number_field="Pol #",
    client_name_field="Named Insured",
    premium_field="Gross Premium",
    # ... fill in remaining fields
)

# Add to registry
CARRIER_REGISTRY["erie"] = ERIE
```

---

## Step 4: Run a Trial Ingestion

```bash
# With the MCP server running, or directly:
python -c "
from mcp_server.tools.ingestion import ingest_statement
result = ingest_statement('path/to/erie_statement.xlsx', 'erie', mode='trial')
print(f'Extracted {len(result[\"raw_rows\"])} rows')
print('Columns:', result.get('columns', []))
"
```

Review the raw rows. Check:
- Are rows being extracted correctly?
- Are there header/footer rows being picked up that should be skipped?
- Is the data in the expected columns?

---

## Step 5: Test Normalization

```bash
python -c "
from mcp_server.tools.ingestion import ingest_statement
from mcp_server.tools.normalization import normalize_raw_rows

raw = ingest_statement('path/to/erie_statement.xlsx', 'erie', mode='trial')
transactions = normalize_raw_rows(raw)

for txn in transactions[:5]:
    print(f'  Policy: {txn.policy_number}')
    print(f'  Client: {txn.client_name}')
    print(f'  Amount: {txn.amount}')
    print(f'  Type:   {txn.transaction_type}')
    print()
"
```

If the LLM is misidentifying fields, adjust the `field_mappings` in the carrier config.

---

## Step 6: Run Trial Mode for 2 Weeks

Use `ingest_carrier_statement` with `mode="trial"` for all Erie statements.
Check the daily monitoring dashboard each morning.

Target metrics before promoting to live:
- **Auto-approval rate ≥ 90%**
- **Policy match rate ≥ 95%**
- **No systematic errors** (same error repeating across many transactions)

---

## Step 7: Get Accounting Team Sign-Off

The accounting team reviews the trial run report and signs off.
They should confirm:
- Amounts look correct
- Policy matching is accurate
- Commission calculations are right

---

## Step 8: Enable Live Mode

Once sign-off is received, update `.env`:
```
# Add carrier-specific live mode enablement
CARRIER_ERIE_MODE=live
```

Or update the `DEFAULT_MODE` only after all initial carriers are validated.

---

## Troubleshooting

**"Carrier not found in registry"**
→ You need to add it to `CARRIER_REGISTRY` in `mcp_server/schemas/carrier_schemas/__init__.py`

**Policy match rate < 80%**
→ Check if the policy number field is being extracted correctly
→ Check if carrier uses a different policy number format than what's in Epic
→ May need custom matching logic (e.g. prefix/suffix stripping)

**LLM normalization returning wrong transaction types**
→ Update the `transaction_type_map` in the carrier schema with the carrier's actual values

**Amounts showing as 0**
→ Check for parentheses `(5000.00)` format for negatives — the parser handles this
→ Check for comma formatting `5,000.00` — the parser handles this
→ Check the column name in `field_mappings`
