"""
Per-carrier field mapping schemas.
Each carrier has a CarrierSchema that tells the ingestion and normalization
layers where to find key fields in that carrier's statement format.

Built from analysis of 71 real carrier statements across 48 carriers.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CarrierSchema:
    """Field mapping for a specific carrier's statement format."""
    carrier_slug: str                          # e.g. "hartford"
    carrier_display_name: str                  # e.g. "The Hartford"

    # Column / field name mappings (match headers in PDF tables or Excel columns)
    policy_number_field: str = "Policy Number"
    client_name_field: str = "Insured Name"
    premium_field: str = "Premium"
    commission_field: str = "Commission"
    effective_date_field: str = "Effective Date"
    expiration_date_field: str = "Expiration Date"
    transaction_type_field: str = "Transaction Type"
    line_of_business_field: str = "Line of Business"
    producer_code_field: str = "Producer"

    # Formatting hints for the normalization LLM
    date_format: str = "MM/DD/YYYY"
    amount_format: str = "standard"            # standard | parentheses_negative | trailing_minus | signed
    rate_format: str = "percentage"            # percentage | bare_integer | scaled_integer
    has_header_row: bool = True
    skip_rows_top: int = 0                     # Rows to skip at the top (letterhead etc.)
    skip_rows_bottom: int = 0                  # Summary/total rows at the bottom
    notes: str = ""                            # Parsing quirks for the LLM

    # Optional portal config for browser automation
    portal_url: Optional[str] = None
    portal_login_selector: Optional[str] = None
    portal_download_selector: Optional[str] = None


# ------------------------------------------------------------------ #
# Carrier Registry — built from real sample data (48 carriers)         #
# ------------------------------------------------------------------ #

CARRIER_REGISTRY: dict[str, CarrierSchema] = {

    # === P&C CARRIERS ===

    "hartford": CarrierSchema(
        carrier_slug="hartford",
        carrier_display_name="The Hartford",
        policy_number_field="Policy Number",
        client_name_field="Named Insured",
        premium_field="Premium",
        commission_field="Comm Amount",
        effective_date_field="Eff Date",
        producer_code_field="Payroll Code",
        rate_format="bare_integer",
        notes="Payroll-billed WC statement. Rates are bare integers (9=9%). Multiple line items per policy for different coverage components.",
    ),
    "hanover": CarrierSchema(
        carrier_slug="hanover",
        carrier_display_name="Hanover Insurance Group",
        policy_number_field="Policy number",
        client_name_field="Insured",  # grouped as section header
        premium_field="Premium",
        commission_field="Amount",
        effective_date_field="Txn eff date",
        transaction_type_field="Txn type",
        line_of_business_field="Product",
        amount_format="parentheses_negative",
        notes="Every transaction has a paired CSC Fee row at 1.50% (deduction). Insured name appears as section header, not in each row. Negatives use parentheses: $(335.00).",
    ),
    "central": CarrierSchema(
        carrier_slug="central",
        carrier_display_name="Central Insurance Companies",
        policy_number_field="POLICY NUMBER",
        client_name_field="INSURED NAME",
        premium_field="PREMIUM AMOUNT",
        commission_field="COMM AMOUNT",
        effective_date_field="INCEP DATE",
        line_of_business_field="LOB",
        transaction_type_field="TRAN",
        amount_format="trailing_minus",
        rate_format="scaled_integer",
        notes="Fixed-width mainframe output. Rates are scaled: 125=12.5%, 090=9%. Negatives use trailing minus: 427.02-. LOB codes: FMH=Homeowners, FMA=Auto, CLP=Commercial, WC=Workers Comp.",
    ),
    "donegal": CarrierSchema(
        carrier_slug="donegal",
        carrier_display_name="Donegal Insurance Group",
        policy_number_field="Policy Number",
        client_name_field="Insured Name",
        premium_field="Premium",
        commission_field="Commission Amount",
        effective_date_field="Inception Date",
        expiration_date_field="Expiration Date",
        line_of_business_field="Line of Business",
        transaction_type_field="Description",
        notes="May contain TWO separate agency statements in one PDF. Description includes (R)=Renewal, (N)=New. Has balance forward and remittance slip.",
    ),
    "liberty": CarrierSchema(
        carrier_slug="liberty",
        carrier_display_name="Liberty Mutual Insurance",
        policy_number_field="POLICY",
        client_name_field="INSURED",
        premium_field="PREMIUM",
        commission_field="AMOUNT",
        effective_date_field="EFF.",
        expiration_date_field="EXP.",
        transaction_type_field="TRAN.",
        line_of_business_field="LINE",
        notes="Summary page + detail page. Transaction codes: NBS=New Business. LINE uses 2-letter codes (BM, etc).",
    ),
    "berkley": CarrierSchema(
        carrier_slug="berkley",
        carrier_display_name="Berkley Net Underwriters",
        policy_number_field="Policy",
        client_name_field="Insured Name",
        premium_field="Commission Basis",
        commission_field="Commission",
        effective_date_field="Eff Date",
        transaction_type_field="Transaction Type",
        notes="Commission Basis = premium amount. Policy numbers prefixed with BNET. Has running account balance (balance forward + disbursements).",
    ),
    "allied": CarrierSchema(
        carrier_slug="allied",
        carrier_display_name="Allied Benefit Systems",
        policy_number_field="Group No.",
        client_name_field="Group Name",
        premium_field="Invoice Total",
        commission_field="Paid Amount",
        producer_code_field="Writing Agent Number",
        rate_format="percentage",
        notes="Benefits/health insurance, NOT P&C. Uses group-level identifiers. Fields: Stoploss Total, Census Count, Calculation Method. Agent rate is a flat percentage.",
    ),
    "westfield": CarrierSchema(
        carrier_slug="westfield",
        carrier_display_name="Westfield Insurance",
        policy_number_field="Policy Number",
        client_name_field="Named Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "state": CarrierSchema(
        carrier_slug="state",
        carrier_display_name="State Auto Insurance",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "progressive": CarrierSchema(
        carrier_slug="progressive",
        carrier_display_name="Progressive Insurance",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "safeco": CarrierSchema(
        carrier_slug="safeco",
        carrier_display_name="Safeco Insurance",
        policy_number_field="Policy Number",
        client_name_field="Named Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "orchid": CarrierSchema(
        carrier_slug="orchid",
        carrier_display_name="Orchid Insurance",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "nippon": CarrierSchema(
        carrier_slug="nippon",
        carrier_display_name="Nippon Insurance",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),

    # === WORKERS COMP ===

    "accident": CarrierSchema(
        carrier_slug="accident",
        carrier_display_name="Accident Fund (AF Group)",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Trans Amt",
        commission_field="Comm Payment",
        effective_date_field="Trans Date",
        transaction_type_field="Trans Type",
        notes="Workers comp. Policy number includes basis code in parentheses e.g. '04(POW)'. Distinguishes Comm Amt vs Non-Comm Amt.",
    ),
    "guard": CarrierSchema(
        carrier_slug="guard",
        carrier_display_name="Guard (Berkley Guard)",
        policy_number_field="col_2",  # No header row
        client_name_field="col_3",
        premium_field="col_5",
        commission_field="col_7",
        effective_date_field="col_4",
        has_header_row=False,
        amount_format="parentheses_negative",
        notes="CSV with NO header row. Columns must be inferred by position. Negatives use parentheses inside quotes. Agency code in col_1.",
    ),

    # === BENEFITS / GROUP CARRIERS ===

    "principal": CarrierSchema(
        carrier_slug="principal",
        carrier_display_name="Principal Financial Group",
        policy_number_field="Customer Account ID",
        client_name_field="Customer Name",
        premium_field="Premium Amount",
        commission_field="Payment Amount",
        effective_date_field="Premium Due Date",
        line_of_business_field="Line of Coverage",
        producer_code_field="Marketer Name",
        notes="Group benefits: LIFE, DENTAL, VISION, STD, LTD. Payment Category Name distinguishes RENEWAL vs FIRST YEAR. Customer names truncated to ~15 chars. Split marketer names with slash indicate shared production credit.",
    ),
    "cigna": CarrierSchema(
        carrier_slug="cigna",
        carrier_display_name="Cigna",
        policy_number_field="Policy Number",
        client_name_field="Account Name",
        premium_field="Premium Amount",
        commission_field="Payment Amount",
        effective_date_field="Statement Date",
        notes="CSV with MIXED ROW TYPES: Line Item column indicates 'Client Detail' (actual data), 'Opening/Previous Balance', 'Closing Balance', 'Total Comp Payment'. Filter by Line Item='Client Detail'. Two comp models: Per Employee and Percent.",
    ),
    "bcbs": CarrierSchema(
        carrier_slug="bcbs",
        carrier_display_name="Blue Cross Blue Shield",
        policy_number_field="POLICY NUMBER",
        client_name_field="NAME / GROUP NAME",
        premium_field="PREMIUM",
        commission_field="PAYMENT",
        effective_date_field="RATE EFFECTIVE DATE",
        line_of_business_field="PRODUCT TYPE",
        notes="Medicare Supplement/Part D. 28 columns. Summary data embedded in top rows before data table. INFO ONLY rows have $0 and must be filtered. Has MEDICARE ID field.",
    ),
    "benecon": CarrierSchema(
        carrier_slug="benecon",
        carrier_display_name="Benecon",
        policy_number_field="Group Number",
        client_name_field="Group Name",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="Benefits administrator. Excel format.",
    ),
    "lincoln": CarrierSchema(
        carrier_slug="lincoln",
        carrier_display_name="Lincoln Financial",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="XLS files are actually HTML tables disguised as Excel. Multiple HTML tables in one file. Agent number in header area.",
    ),
    "unum": CarrierSchema(
        carrier_slug="unum",
        carrier_display_name="Unum Group",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="Group benefits. PDF text-only format requiring LLM extraction.",
    ),
    "sun": CarrierSchema(
        carrier_slug="sun",
        carrier_display_name="Sun Life Financial",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="PDF text-only format requiring LLM extraction.",
    ),
    "guardian": CarrierSchema(
        carrier_slug="guardian",
        carrier_display_name="Guardian Life Insurance",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "beam": CarrierSchema(
        carrier_slug="beam",
        carrier_display_name="Beam Dental",
        policy_number_field="Policy Number",
        client_name_field="Group Name",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "dearborn": CarrierSchema(
        carrier_slug="dearborn",
        carrier_display_name="Dearborn National (Dearborn Group)",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),

    # === SPECIALTY / SURPLUS ===

    "amtrust": CarrierSchema(
        carrier_slug="amtrust",
        carrier_display_name="AmTrust Financial",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "amwins": CarrierSchema(
        carrier_slug="amwins",
        carrier_display_name="Amwins Group",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="Wholesale broker. Excel format.",
    ),
    "cna": CarrierSchema(
        carrier_slug="cna",
        carrier_display_name="CNA Insurance",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "sentry": CarrierSchema(
        carrier_slug="sentry",
        carrier_display_name="Sentry Insurance",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "sas": CarrierSchema(
        carrier_slug="sas",
        carrier_display_name="SAS (Southern Automotive Solutions)",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "summit": CarrierSchema(
        carrier_slug="summit",
        carrier_display_name="Summit Insurance",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="Large Excel files (235+ rows).",
    ),
    "priority": CarrierSchema(
        carrier_slug="priority",
        carrier_display_name="Priority Risk Insurance",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="Excel format.",
    ),
    "cason": CarrierSchema(
        carrier_slug="cason",
        carrier_display_name="Cason Group",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="Excel format. Large bordereaux files.",
    ),

    # === FLOOD / SPECIALTY ===

    "assurant": CarrierSchema(
        carrier_slug="assurant",
        carrier_display_name="Assurant Flood",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="Flood insurance specialist.",
    ),
    "appalachian": CarrierSchema(
        carrier_slug="appalachian",
        carrier_display_name="Appalachian Underwriters",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "memic": CarrierSchema(
        carrier_slug="memic",
        carrier_display_name="MEMIC",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="Workers compensation. PDF text-only.",
    ),
    "ffva": CarrierSchema(
        carrier_slug="ffva",
        carrier_display_name="FFVA Mutual",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "genworth": CarrierSchema(
        carrier_slug="genworth",
        carrier_display_name="Genworth Financial",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="CSV format.",
    ),
    "protective": CarrierSchema(
        carrier_slug="protective",
        carrier_display_name="Protective Insurance",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="CSV format.",
    ),
    "prudential": CarrierSchema(
        carrier_slug="prudential",
        carrier_display_name="Prudential Financial",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "standard": CarrierSchema(
        carrier_slug="standard",
        carrier_display_name="Standard Insurance",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
    "western": CarrierSchema(
        carrier_slug="western",
        carrier_display_name="Western Surety",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
        notes="Surety bonds.",
    ),
    "american": CarrierSchema(
        carrier_slug="american",
        carrier_display_name="American Modern Insurance",
        policy_number_field="Policy Number",
        client_name_field="Insured",
        premium_field="Premium",
        commission_field="Commission",
        effective_date_field="Effective Date",
    ),
}


def get_carrier_schema(carrier: str) -> CarrierSchema:
    """
    Look up carrier schema by slug. Falls back to a generic default
    if the carrier isn't registered yet (the LLM normalization layer
    will still attempt to map fields).
    """
    if carrier.lower() in CARRIER_REGISTRY:
        return CARRIER_REGISTRY[carrier.lower()]

    # Fallback: generic schema — the normalization LLM will do its best
    return CarrierSchema(
        carrier_slug=carrier.lower(),
        carrier_display_name=carrier.title(),
    )
