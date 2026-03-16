-- ============================================================
-- Carrier Accounting MCP — BigQuery Table Definitions
-- Run these in BigQuery console or via bq CLI before first use
-- ============================================================

-- 1. Create datasets
-- bq mk --dataset snellings-walters-prod:sw_carrier_accounting
-- bq mk --dataset snellings-walters-prod:sw_staging


-- ============================================================
-- SHADOW TABLE (trial mode writes)
-- ============================================================
CREATE TABLE IF NOT EXISTS `sw_staging.carrier_entries_shadow` (
    transaction_id      STRING    NOT NULL,
    run_id              STRING    NOT NULL,
    source_file         STRING,
    source_row          INT64,

    -- Carrier & Policy
    carrier             STRING,
    policy_number       STRING,
    epic_policy_id      STRING,
    epic_client_id      STRING,
    client_name         STRING,
    producer_code       STRING,

    -- Transaction
    transaction_type    STRING,
    effective_date      DATE,
    expiration_date     DATE,
    statement_date      DATE,
    amount              NUMERIC,
    commission_rate     NUMERIC,
    line_of_business    STRING,
    description         STRING,

    -- Confidence & Validation
    confidence_score    FLOAT64,
    confidence_factors  JSON,
    validation_warnings JSON,
    validation_errors   JSON,

    -- Workflow
    status              STRING,      -- pending|validated|review|approved|rejected|posted|failed|rolled_back
    mode                STRING,      -- trial|live
    auto_approved       BOOL,
    reviewed_by         STRING,
    review_notes        STRING,
    reviewed_at         TIMESTAMP,

    -- Epic Write
    epic_entry_id       STRING,
    epic_posted_at      TIMESTAMP,

    -- Metadata
    created_at          TIMESTAMP   NOT NULL,
    updated_at          TIMESTAMP
)
PARTITION BY DATE(created_at)
CLUSTER BY carrier, status, run_id
OPTIONS (
    description = 'Trial mode shadow table — zero Epic writes, for accounting team review',
    partition_expiration_days = 365
);


-- ============================================================
-- LIVE TABLE (approved and posted transactions)
-- ============================================================
CREATE TABLE IF NOT EXISTS `sw_carrier_accounting.carrier_entries_live` (
    transaction_id      STRING    NOT NULL,
    run_id              STRING    NOT NULL,
    source_file         STRING,
    source_row          INT64,

    carrier             STRING,
    policy_number       STRING,
    epic_policy_id      STRING,
    epic_client_id      STRING,
    client_name         STRING,
    producer_code       STRING,

    transaction_type    STRING,
    effective_date      DATE,
    expiration_date     DATE,
    statement_date      DATE,
    amount              NUMERIC,
    commission_rate     NUMERIC,
    line_of_business    STRING,
    description         STRING,

    confidence_score    FLOAT64,
    confidence_factors  JSON,
    validation_warnings JSON,
    validation_errors   JSON,

    status              STRING,
    mode                STRING,
    auto_approved       BOOL,
    reviewed_by         STRING,
    review_notes        STRING,
    reviewed_at         TIMESTAMP,

    epic_entry_id       STRING,
    epic_posted_at      TIMESTAMP,

    created_at          TIMESTAMP   NOT NULL,
    updated_at          TIMESTAMP
)
PARTITION BY DATE(created_at)
CLUSTER BY carrier, status, epic_policy_id
OPTIONS (
    description = 'Live approved transactions — written to Applied Epic'
);


-- ============================================================
-- RUN LOG
-- ============================================================
CREATE TABLE IF NOT EXISTS `sw_carrier_accounting.run_log` (
    run_id              STRING    NOT NULL,
    source_file         STRING,
    carrier             STRING,
    mode                STRING,
    total_transactions  INT64,
    auto_approved       INT64,
    review_queue        INT64,
    failed              INT64,
    posted_to_epic      INT64,
    total_amount        NUMERIC,
    started_at          TIMESTAMP,
    completed_at        TIMESTAMP,
    status              STRING      -- running|completed|failed|rolled_back
)
OPTIONS (
    description = 'One row per ingestion run — summary statistics'
);


-- ============================================================
-- AUDIT TRAIL
-- ============================================================
CREATE TABLE IF NOT EXISTS `sw_carrier_accounting.audit_trail` (
    audit_id            STRING    NOT NULL,
    transaction_id      STRING,
    run_id              STRING,
    action              STRING,     -- ingested|normalized|validated|staged|approved|rejected|posted|rolled_back
    performed_by        STRING,     -- 'system' or reviewer name
    details             JSON,
    created_at          TIMESTAMP   NOT NULL
)
PARTITION BY DATE(created_at)
OPTIONS (
    description = 'Full lineage audit trail: source file → Epic entry ID'
);
