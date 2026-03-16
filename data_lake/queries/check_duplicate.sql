-- Check if an identical transaction already exists
SELECT COUNT(*) AS cnt
FROM `{project}.{dataset}.carrier_entries_live`
WHERE
    carrier = @carrier
    AND policy_number = @policy_number
    AND amount = CAST(@amount AS NUMERIC)
    AND effective_date = @effective_date
    AND status NOT IN ('rejected', 'rolled_back')
