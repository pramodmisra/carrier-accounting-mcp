-- Daily scorecard metrics for the monitoring dashboard
WITH combined AS (
    SELECT * FROM `{project}.sw_staging.carrier_entries_shadow` WHERE mode = 'trial'
    UNION ALL
    SELECT * FROM `{project}.sw_carrier_accounting.carrier_entries_live` WHERE mode = 'live'
)
SELECT
    COUNT(*) AS total_transactions,
    COUNTIF(status IN ('approved', 'posted'))         AS auto_approved,
    COUNTIF(status = 'review')                        AS review_queue,
    COUNTIF(status = 'failed')                        AS failed,
    COUNTIF(status = 'posted')                        AS posted_to_epic,
    COUNTIF(status = 'rejected')                      AS rejected,
    AVG(confidence_score)                             AS avg_confidence,
    SUM(CAST(amount AS NUMERIC))                      AS total_amount
FROM combined
WHERE DATE(created_at) = @target_date
