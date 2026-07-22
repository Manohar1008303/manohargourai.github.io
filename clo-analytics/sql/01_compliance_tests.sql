-- =====================================================================
--  01 — CLO INDENTURE COMPLIANCE TESTING
--  Coverage tests (OC/IC), collateral-quality tests (WARF/WAS) and
--  concentration limits — the core of CLO trustee compliance monitoring.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1.1  Current-period compliance scorecard (latest period per deal)
--      One row per test with pass/fail and cushion to the trigger.
-- ---------------------------------------------------------------------
WITH latest AS (
    SELECT deal_id, MAX(period) AS period
    FROM compliance_tests GROUP BY deal_id
)
SELECT  d.deal_name,
        c.period,
        c.test_category,
        c.test_name,
        c.threshold_type,
        c.threshold_value,
        c.actual_value,
        -- cushion: how far inside the limit we are (positive = passing)
        CASE c.threshold_type
             WHEN 'min' THEN ROUND(c.actual_value - c.threshold_value, 2)
             ELSE            ROUND(c.threshold_value - c.actual_value, 2)
        END AS cushion,
        c.result
FROM        compliance_tests c
JOIN        latest  l ON l.deal_id = c.deal_id AND l.period = c.period
JOIN        deals   d ON d.deal_id = c.deal_id
ORDER BY    d.deal_name,
            CASE c.test_category WHEN 'Coverage' THEN 1
                                 WHEN 'Collateral Quality' THEN 2 ELSE 3 END,
            c.test_name;

-- ---------------------------------------------------------------------
-- 1.2  All current failing tests — the daily "exceptions" worklist
-- ---------------------------------------------------------------------
WITH latest AS (
    SELECT deal_id, MAX(period) AS period FROM compliance_tests GROUP BY deal_id
)
SELECT  d.deal_name, c.test_category, c.test_name,
        c.threshold_value, c.actual_value,
        CASE c.threshold_type WHEN 'min'
             THEN ROUND(c.actual_value - c.threshold_value,2)
             ELSE ROUND(c.threshold_value - c.actual_value,2) END AS cushion
FROM        compliance_tests c
JOIN        latest l ON l.deal_id=c.deal_id AND l.period=c.period
JOIN        deals  d ON d.deal_id=c.deal_id
WHERE       c.result = 'FAIL'
ORDER BY    cushion ASC;      -- worst breaches first

-- ---------------------------------------------------------------------
-- 1.3  Pass-rate summary by deal and test category
-- ---------------------------------------------------------------------
SELECT  d.deal_name,
        c.test_category,
        COUNT(*)                                              AS tests_run,
        SUM(CASE WHEN c.result='FAIL' THEN 1 ELSE 0 END)      AS failures,
        ROUND(100.0*SUM(CASE WHEN c.result='PASS' THEN 1 END)/COUNT(*),1) AS pass_rate_pct
FROM        compliance_tests c
JOIN        deals d ON d.deal_id=c.deal_id
GROUP BY    d.deal_name, c.test_category
ORDER BY    d.deal_name, c.test_category;

-- ---------------------------------------------------------------------
-- 1.4  OC / IC coverage-cushion TREND across periods (early-warning view)
--      Shrinking cushion flags a deteriorating deal before it breaches.
-- ---------------------------------------------------------------------
SELECT  d.deal_name, c.period, c.test_name,
        c.threshold_value AS trigger_pct,
        c.actual_value    AS actual_pct,
        ROUND(c.actual_value - c.threshold_value, 2) AS cushion_pct
FROM        compliance_tests c
JOIN        deals d ON d.deal_id=c.deal_id
WHERE       c.test_category='Coverage'
ORDER BY    d.deal_name, c.test_name, c.period;

-- ---------------------------------------------------------------------
-- 1.5  Independent WARF recomputation from the loan tape
--      Re-derives the collateral-quality metric straight from assets so
--      the trustee-reported figure can be validated (a control check).
-- ---------------------------------------------------------------------
SELECT  d.deal_name,
        ROUND(SUM(rs.rating_factor * a.par_amount) / SUM(a.par_amount), 0) AS warf_recomputed,
        2900 AS warf_limit,
        CASE WHEN SUM(rs.rating_factor*a.par_amount)/SUM(a.par_amount) <= 2900
             THEN 'PASS' ELSE 'FAIL' END AS result
FROM        assets a
JOIN        rating_scale rs ON rs.moodys_rating = a.moodys_rating
JOIN        deals d        ON d.deal_id = a.deal_id
WHERE       a.is_defaulted = 0
GROUP BY    d.deal_name;
