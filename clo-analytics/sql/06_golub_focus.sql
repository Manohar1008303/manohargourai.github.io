-- =====================================================================
--  06 — FEATURED CLIENT: GOLUB CAPITAL  (client 360)
--  A single-client deep dive on Golub Capital Partners CLO 2024-1, the
--  flagship middle-market deal. Pulls together the compliance, waterfall,
--  portfolio and reconciliation views for one client — the way a lead
--  analyst would prep a client review pack.
--  (Deal id: CLO-GOLB-241)
-- =====================================================================

-- ---------------------------------------------------------------------
-- 6.1  Golub deal profile & collateral snapshot
-- ---------------------------------------------------------------------
SELECT  d.deal_name, d.manager, d.deal_type, d.trustee,
        d.closing_date, d.reinvestment_end, d.stated_maturity,
        printf('%,.0f', d.target_par)                       AS target_par,
        COUNT(a.asset_id)                                   AS num_loans,
        COUNT(DISTINCT a.obligor_id)                        AS num_obligors,
        printf('%,.0f', SUM(a.par_amount))                  AS collateral_par,
        ROUND(SUM(rs.rating_factor*a.par_amount)/SUM(a.par_amount),0) AS warf,
        ROUND(SUM(a.coupon_spread_bps*a.par_amount)/SUM(a.par_amount),1) AS wavg_spread_bps,
        ROUND(100.0*SUM(CASE WHEN a.lien_type='First Lien' THEN a.par_amount END)/SUM(a.par_amount),1) AS first_lien_pct
FROM        deals d
JOIN        assets a  ON a.deal_id = d.deal_id
JOIN        rating_scale rs ON rs.moodys_rating = a.moodys_rating
WHERE       d.deal_id = 'CLO-GOLB-241'
GROUP BY    d.deal_name, d.manager, d.deal_type, d.trustee,
            d.closing_date, d.reinvestment_end, d.stated_maturity, d.target_par;

-- ---------------------------------------------------------------------
-- 6.2  Golub capital structure (tranche stack) with triggers
-- ---------------------------------------------------------------------
SELECT  t.class_name, t.moodys_rating, t.seniority_rank,
        printf('%,.0f', t.original_balance)  AS balance,
        t.coupon_spread_bps                  AS spread_bps,
        t.oc_trigger_pct, t.ic_trigger_pct,
        CASE WHEN t.is_deferrable=1 THEN 'Yes' ELSE 'No' END AS pik_able
FROM        tranches t
WHERE       t.deal_id = 'CLO-GOLB-241'
ORDER BY    t.seniority_rank;

-- ---------------------------------------------------------------------
-- 6.3  Golub — latest-period compliance scorecard (with cushion)
-- ---------------------------------------------------------------------
SELECT  test_category, test_name, threshold_type,
        threshold_value, ROUND(actual_value,2) AS actual_value,
        ROUND(cushion,2) AS cushion, result
FROM        v_compliance_scorecard
WHERE       deal_id = 'CLO-GOLB-241'
ORDER BY    CASE test_category WHEN 'Coverage' THEN 1
                               WHEN 'Collateral Quality' THEN 2 ELSE 3 END,
            test_name;

-- ---------------------------------------------------------------------
-- 6.4  Golub — interest waterfall for the latest period
-- ---------------------------------------------------------------------
WITH latest AS (SELECT MAX(period) p FROM distributions WHERE deal_id='CLO-GOLB-241')
SELECT  dist.waterfall_step AS step, t.class_name, t.moodys_rating,
        printf('%,.0f', dist.interest_due)       AS interest_due,
        printf('%,.0f', dist.interest_paid)      AS interest_paid,
        printf('%,.0f', dist.deferred_interest)  AS deferred_pik
FROM        distributions dist
JOIN        tranches t ON t.tranche_id = dist.tranche_id
WHERE       dist.deal_id='CLO-GOLB-241'
  AND       dist.period = (SELECT p FROM latest)
ORDER BY    dist.waterfall_step;

-- ---------------------------------------------------------------------
-- 6.5  Golub — top 10 obligor exposures (single-obligor 2% cap)
-- ---------------------------------------------------------------------
SELECT  o.obligor_name, o.moodys_rating, o.industry,
        printf('%,.0f', SUM(a.par_amount)) AS par,
        ROUND(100.0*SUM(a.par_amount)/(SELECT SUM(par_amount) FROM assets WHERE deal_id='CLO-GOLB-241'),2) AS pct_of_deal,
        CASE WHEN 100.0*SUM(a.par_amount)/(SELECT SUM(par_amount) FROM assets WHERE deal_id='CLO-GOLB-241') > 2
             THEN 'OVER LIMIT' ELSE 'ok' END AS flag
FROM        assets a
JOIN        obligors o ON o.obligor_id = a.obligor_id
WHERE       a.deal_id = 'CLO-GOLB-241'
GROUP BY    o.obligor_name, o.moodys_rating, o.industry
ORDER BY    SUM(a.par_amount) DESC
LIMIT 10;

-- ---------------------------------------------------------------------
-- 6.6  Golub — trustee reconciliation status & open breaks
-- ---------------------------------------------------------------------
SELECT  break_type,
        COUNT(*)                                AS num_positions,
        printf('%,.0f', SUM(ABS(break_amount))) AS abs_exposure,
        ROUND(AVG(age_days),1)                  AS avg_age_days
FROM        trustee_positions
WHERE       deal_id = 'CLO-GOLB-241'
GROUP BY    break_type
ORDER BY    SUM(ABS(break_amount)) DESC;

-- ---------------------------------------------------------------------
-- 6.7  Golub — escalation worklist (aged, open breaks)
-- ---------------------------------------------------------------------
SELECT  tp.asset_id, o.obligor_name, a.facility_name, tp.break_type,
        printf('%,.0f', tp.internal_par) AS internal_par,
        printf('%,.0f', tp.trustee_par)  AS trustee_par,
        printf('%,.0f', tp.break_amount) AS break_amount,
        tp.age_days, tp.status
FROM        trustee_positions tp
JOIN        assets   a ON a.asset_id = tp.asset_id
JOIN        obligors o ON o.obligor_id = a.obligor_id
WHERE       tp.deal_id = 'CLO-GOLB-241'
  AND       tp.status = 'Escalated'
ORDER BY    tp.age_days DESC, ABS(tp.break_amount) DESC;
