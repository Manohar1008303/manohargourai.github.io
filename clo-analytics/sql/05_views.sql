-- =====================================================================
--  05 — REPORTING VIEWS
--  Reusable views that flatten the model for BI tools (Power BI / Tableau)
--  and for the dashboard. Run once; then SELECT * FROM the view.
-- =====================================================================

DROP VIEW IF EXISTS v_portfolio_summary;
DROP VIEW IF EXISTS v_compliance_scorecard;
DROP VIEW IF EXISTS v_recon_summary;
DROP VIEW IF EXISTS v_asset_detail;

-- Deal-level collateral summary (one row per deal)
CREATE VIEW v_portfolio_summary AS
SELECT  d.deal_id, d.deal_name, d.deal_type, d.manager,
        COUNT(*)                         AS num_loans,
        COUNT(DISTINCT a.obligor_id)     AS num_obligors,
        SUM(a.par_amount)                AS collateral_par,
        SUM(rs.rating_factor*a.par_amount)/SUM(a.par_amount)                       AS warf,
        SUM(a.coupon_spread_bps*a.par_amount)/SUM(a.par_amount)                    AS wavg_spread_bps,
        SUM(a.market_price*a.par_amount)/SUM(a.par_amount)                         AS wavg_price,
        100.0*SUM(CASE WHEN a.is_defaulted=1 THEN a.par_amount END)/SUM(a.par_amount) AS defaulted_pct,
        100.0*SUM(CASE WHEN rs.is_ccc=1     THEN a.par_amount END)/SUM(a.par_amount) AS ccc_pct
FROM        assets a
JOIN        rating_scale rs ON rs.moodys_rating=a.moodys_rating
JOIN        deals d ON d.deal_id=a.deal_id
GROUP BY    d.deal_id, d.deal_name, d.deal_type, d.manager;

-- Latest-period compliance scorecard with cushion
CREATE VIEW v_compliance_scorecard AS
WITH latest AS (SELECT deal_id, MAX(period) period FROM compliance_tests GROUP BY deal_id)
SELECT  d.deal_id, d.deal_name, c.period, c.test_category, c.test_name,
        c.threshold_type, c.threshold_value, c.actual_value,
        CASE c.threshold_type WHEN 'min' THEN c.actual_value-c.threshold_value
                              ELSE c.threshold_value-c.actual_value END AS cushion,
        c.result
FROM        compliance_tests c
JOIN        latest l ON l.deal_id=c.deal_id AND l.period=c.period
JOIN        deals  d ON d.deal_id=c.deal_id;

-- Reconciliation summary by deal
CREATE VIEW v_recon_summary AS
SELECT  d.deal_id, d.deal_name,
        COUNT(*) AS positions,
        SUM(CASE WHEN break_type='Matched' THEN 1 ELSE 0 END)  AS matched,
        SUM(CASE WHEN break_type<>'Matched' THEN 1 ELSE 0 END) AS breaks,
        100.0*SUM(CASE WHEN break_type='Matched' THEN 1 END)/COUNT(*) AS match_rate_pct,
        SUM(ABS(break_amount)) AS gross_break_exposure
FROM        trustee_positions tp
JOIN        deals d ON d.deal_id=tp.deal_id
GROUP BY    d.deal_id, d.deal_name;

-- Fully denormalised asset tape (BI fact table)
CREATE VIEW v_asset_detail AS
SELECT  a.asset_id, d.deal_name, d.deal_type, o.obligor_name, o.industry, o.country,
        a.facility_name, a.lien_type, a.par_amount, a.market_price,
        a.coupon_spread_bps, a.moodys_rating, rs.rating_factor, rs.is_ccc,
        a.is_defaulted, a.is_cov_lite, a.maturity_date
FROM        assets a
JOIN        obligors o ON o.obligor_id=a.obligor_id
JOIN        deals    d ON d.deal_id=a.deal_id
JOIN        rating_scale rs ON rs.moodys_rating=a.moodys_rating;
