-- ============================================================
-- Audit Trail DDL — Full lineage: source file -> Epic entry ID
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
    description = 'Full lineage audit trail: source file -> Epic entry ID'
);
