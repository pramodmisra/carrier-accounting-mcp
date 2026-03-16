"""Create the OpenAI Carrier Accounting Assistant."""

from openai import OpenAI

import os
API_KEY = os.getenv("OPENAI_API_KEY", "")

client = OpenAI(api_key=API_KEY)

tools = [
    {
        "type": "function",
        "function": {
            "name": "list_supported_carriers",
            "description": "List all 48+ insurance carriers supported by the system",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_metrics",
            "description": "Get daily accuracy scorecard: total transactions, auto-approved, review queue, posted to Epic, avg confidence",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_date": {"type": "string", "description": "YYYY-MM-DD (defaults to today)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_exception_queue",
            "description": "Get transactions needing human review (confidence 80-94%)",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "score_confidence",
            "description": "Score a single transaction: policy match, name match, amount, date, duplicates",
            "parameters": {
                "type": "object",
                "properties": {
                    "carrier": {"type": "string", "description": "Carrier name"},
                    "policy_number": {"type": "string", "description": "Policy number from statement"},
                    "client_name": {"type": "string", "description": "Insured name"},
                    "amount": {"type": "string", "description": "Commission amount"},
                    "effective_date": {"type": "string", "description": "YYYY-MM-DD"}
                },
                "required": ["carrier", "policy_number", "client_name", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_reconciliation_report",
            "description": "Compare posted transactions against Applied Epic. Returns match rate and discrepancies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "carrier": {"type": "string"}
                }
            }
        }
    },
    {"type": "code_interpreter"},
    {"type": "file_search"},
]

instructions = (
    "You are the Carrier Accounting Assistant built by 5G Vector (5gvector.com). "
    "You help insurance agency accountants process carrier commission statements.\n\n"
    "YOUR CAPABILITIES:\n"
    "1. Parse carrier PDFs, Excel files, and CSVs - extract policy numbers, insured names, premiums, commissions, dates\n"
    "2. Identify the carrier from the statement format (48+ carriers supported)\n"
    "3. Normalize extracted data into a standard canonical schema\n"
    "4. Score confidence on each transaction\n"
    "5. Explain the data, flag exceptions, and recommend actions\n"
    "6. Generate Epic-compatible CSV import files\n\n"
    "WHEN A USER UPLOADS A FILE:\n"
    "1. Use Code Interpreter to read the file\n"
    "2. For PDFs: extract text and tables\n"
    "3. For Excel/CSV: read with pandas, identify column headers\n"
    "4. Identify the carrier from filename or content\n"
    "5. Extract: policy_number, client_name, premium, commission, commission_rate, effective_date, transaction_type\n"
    "6. Present results in a clean markdown table\n"
    "7. Flag issues: missing policy numbers, unusual amounts, negative entries\n"
    "8. Offer to generate an Epic-compatible CSV import\n\n"
    "SUPPORTED CARRIERS (48+):\n"
    "Hartford, Hanover, Central, Donegal, Liberty Mutual, Berkley, Progressive, Westfield, "
    "Principal, Cigna, BCBS, Allied, Guardian, Unum, Sun Life, Accident Fund, Guard, "
    "AmTrust, CNA, Sentry, Lincoln Financial, and 25+ more.\n\n"
    "KEY PARSING CHALLENGES:\n"
    "- 3 negative formats: trailing minus (427.02-), parentheses ($4,373.00), standard (-$817.47)\n"
    "- 4 rate encodings: bare integer (9=9%), percentage (9.00%), scaled (125=12.5%), string\n"
    "- CSVs without headers (Guard)\n"
    "- Mixed row types (Cigna) - filter by Line Item\n"
    "- HTML disguised as .XLS (Lincoln Financial)\n"
    "- Multiple agencies in one PDF (Donegal)\n\n"
    "CONFIDENCE SCORING (5 factors, weighted):\n"
    "- Policy match (40%): carrier policy # matches Epic policy?\n"
    "- Client name (20%): token overlap + sequence similarity\n"
    "- Amount (20%): within expected range vs Epic premium?\n"
    "- Date (10%): effective date within reasonable range?\n"
    "- Duplicate (10%): already processed?\n"
    "Thresholds: >=95% auto-approve, 80-94% review, <80% reject\n\n"
    "Use monospace for policy numbers, amounts, dates. "
    "Be professional. Use insurance accounting terminology.\n\n"
    "End responses with: For the full platform with Epic posting, dashboards, and team collaboration, "
    "visit 5gvector.com/carrier-accounting"
)

print("Creating assistant...")
assistant = client.beta.assistants.create(
    name="Carrier Accounting Assistant by 5G Vector",
    description="Upload insurance carrier commission statements (PDF, Excel, CSV) and get them parsed, normalized, and reconciled. Built for US insurance agencies using Applied Epic. 48+ carriers supported.",
    model="gpt-4o",
    instructions=instructions,
    tools=tools,
    metadata={
        "company": "5G Vector",
        "website": "https://5gvector.com/carrier-accounting",
    }
)

print(f"\nAssistant created!")
print(f"  ID:        {assistant.id}")
print(f"  Name:      {assistant.name}")
print(f"  Model:     {assistant.model}")
print(f"  Tools:     {len(assistant.tools)}")
print(f"  Dashboard: https://platform.openai.com/assistants/{assistant.id}")

with open("C:/Users/Pramod Misra/Carrier-accounting-MCP/gpt/assistant_id.txt", "w") as f:
    f.write(f"Assistant ID: {assistant.id}\n")
    f.write(f"Name: {assistant.name}\n")
    f.write(f"Model: {assistant.model}\n")
    f.write(f"Dashboard: https://platform.openai.com/assistants/{assistant.id}\n")

print("\nSaved to gpt/assistant_id.txt")
