-- Validate a carrier policy number against the Epic policy master
SELECT
    PolicyId           AS epic_policy_id,
    ClientId           AS epic_client_id,
    ClientName         AS client_name,
    PolicyNumber       AS epic_policy_number,
    CarrierPolicyNum   AS carrier_policy_number,
    best_billed_premium,
    best_premium,
    LineOfBusiness     AS line_of_business,
    ProducerCode       AS producer_code,
    PolicyStatus       AS policy_status
FROM `{project}.{dataset}.combined_policy_master`
WHERE
    LOWER(CarrierName) LIKE LOWER(@carrier)
    AND (
        CarrierPolicyNum = @policy_number
        OR PolicyNumber  = @policy_number
    )
LIMIT 1
