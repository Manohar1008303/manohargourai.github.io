-- =====================================================================
--  04 — TRUSTEE RECONCILIATION
--  Compares trustee-reported par against internal book records, classifies
--  breaks, ages them, and drives the escalation worklist — mirroring daily
--  cash / position reconciliation controls.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 4.1  Reconciliation summary by deal (match rate + break exposure)
-- ---------------------------------------------------------------------
SELECT  d.deal_name,
        COUNT(*)                                                        AS positions,
        SUM(CASE WHEN break_type='Matched' THEN 1 ELSE 0 END)           AS matched,
        SUM(CASE WHEN break_type<>'Matched' THEN 1 ELSE 0 END)          AS breaks,
        ROUND(100.0*SUM(CASE WHEN break_type='Matched' THEN 1 END)/COUNT(*),1) AS match_rate_pct,
        printf('%,.0f', SUM(ABS(break_amount)))                         AS gross_break_exposure
FROM        trustee_positions tp
JOIN        deals d ON d.deal_id=tp.deal_id
GROUP BY    d.deal_name
ORDER BY    match_rate_pct;

-- ---------------------------------------------------------------------
-- 4.2  Break composition by type
-- ---------------------------------------------------------------------
SELECT  break_type,
        COUNT(*)                                AS num_breaks,
        printf('%,.0f', SUM(ABS(break_amount))) AS abs_exposure,
        ROUND(AVG(age_days),1)                  AS avg_age_days
FROM        trustee_positions
WHERE       break_type<>'Matched'
GROUP BY    break_type
ORDER BY    SUM(ABS(break_amount)) DESC;

-- ---------------------------------------------------------------------
-- 4.3  Aged-break analysis — bucketed by age (SLA / escalation view)
--      Breaks over 15 days are escalation candidates.
-- ---------------------------------------------------------------------
SELECT  CASE
            WHEN age_days=0            THEN '0 (matched)'
            WHEN age_days BETWEEN 1 AND 5  THEN '1-5 days'
            WHEN age_days BETWEEN 6 AND 15 THEN '6-15 days'
            WHEN age_days BETWEEN 16 AND 30 THEN '16-30 days'
            ELSE '30+ days'
        END AS age_bucket,
        COUNT(*)                                AS num_positions,
        printf('%,.0f', SUM(ABS(break_amount))) AS abs_exposure
FROM        trustee_positions
WHERE       break_type<>'Matched'
GROUP BY    age_bucket
ORDER BY    MIN(age_days);

-- ---------------------------------------------------------------------
-- 4.4  Escalation worklist — open, aged breaks needing action first
-- ---------------------------------------------------------------------
SELECT  d.deal_name, tp.asset_id, o.obligor_name, a.facility_name,
        tp.break_type,
        printf('%,.0f', tp.internal_par) AS internal_par,
        printf('%,.0f', tp.trustee_par)  AS trustee_par,
        printf('%,.0f', tp.break_amount) AS break_amount,
        tp.age_days, tp.status
FROM        trustee_positions tp
JOIN        assets   a ON a.asset_id=tp.asset_id
JOIN        obligors o ON o.obligor_id=a.obligor_id
JOIN        deals    d ON d.deal_id=tp.deal_id
WHERE       tp.status='Escalated'
ORDER BY    tp.age_days DESC, ABS(tp.break_amount) DESC
LIMIT 25;

-- ---------------------------------------------------------------------
-- 4.5  Largest position breaks by absolute exposure (top 15)
-- ---------------------------------------------------------------------
SELECT  d.deal_name, tp.asset_id, o.obligor_name, tp.break_type,
        printf('%,.0f', tp.internal_par) AS internal_par,
        printf('%,.0f', tp.trustee_par)  AS trustee_par,
        printf('%,.0f', tp.break_amount) AS break_amount,
        tp.age_days, tp.status
FROM        trustee_positions tp
JOIN        assets   a ON a.asset_id=tp.asset_id
JOIN        obligors o ON o.obligor_id=a.obligor_id
JOIN        deals    d ON d.deal_id=tp.deal_id
WHERE       tp.break_type<>'Matched'
ORDER BY    ABS(tp.break_amount) DESC
LIMIT 15;
