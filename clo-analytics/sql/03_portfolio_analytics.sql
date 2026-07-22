-- =====================================================================
--  03 — PORTFOLIO & CREDIT ANALYTICS
--  Composition, credit quality and risk concentrations of the
--  collateral pool underlying each CLO.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 3.1  Deal-level portfolio summary card
-- ---------------------------------------------------------------------
SELECT  d.deal_name,
        d.deal_type,
        COUNT(*)                                         AS num_loans,
        COUNT(DISTINCT a.obligor_id)                     AS num_obligors,
        printf('%,.0f', SUM(a.par_amount))               AS collateral_par,
        ROUND(SUM(rs.rating_factor*a.par_amount)/SUM(a.par_amount),0) AS warf,
        ROUND(SUM(a.coupon_spread_bps*a.par_amount)/SUM(a.par_amount),1) AS wavg_spread_bps,
        ROUND(SUM(a.market_price*a.par_amount)/SUM(a.par_amount),2)   AS wavg_price,
        ROUND(100.0*SUM(CASE WHEN a.is_defaulted=1 THEN a.par_amount END)/SUM(a.par_amount),2) AS defaulted_pct,
        ROUND(100.0*SUM(CASE WHEN rs.is_ccc=1 THEN a.par_amount END)/SUM(a.par_amount),2)      AS ccc_pct,
        ROUND(100.0*SUM(CASE WHEN a.is_cov_lite=1 THEN a.par_amount END)/SUM(a.par_amount),1)  AS cov_lite_pct
FROM        assets a
JOIN        rating_scale rs ON rs.moodys_rating=a.moodys_rating
JOIN        deals d ON d.deal_id=a.deal_id
GROUP BY    d.deal_name, d.deal_type
ORDER BY    d.deal_name;

-- ---------------------------------------------------------------------
-- 3.2  Rating distribution (par-weighted) across the whole book
-- ---------------------------------------------------------------------
SELECT  a.moodys_rating,
        rs.rank_order,
        COUNT(*)                                    AS num_loans,
        printf('%,.0f', SUM(a.par_amount))          AS par,
        ROUND(100.0*SUM(a.par_amount)/
              (SELECT SUM(par_amount) FROM assets),2) AS pct_of_book
FROM        assets a
JOIN        rating_scale rs ON rs.moodys_rating=a.moodys_rating
GROUP BY    a.moodys_rating, rs.rank_order
ORDER BY    rs.rank_order;

-- ---------------------------------------------------------------------
-- 3.3  Industry concentration with limit check (12% single-industry cap)
-- ---------------------------------------------------------------------
SELECT  d.deal_name,
        o.industry,
        printf('%,.0f', SUM(a.par_amount)) AS par,
        ROUND(100.0*SUM(a.par_amount)/
              SUM(SUM(a.par_amount)) OVER (PARTITION BY d.deal_name),2) AS pct_of_deal,
        CASE WHEN 100.0*SUM(a.par_amount)/
                  SUM(SUM(a.par_amount)) OVER (PARTITION BY d.deal_name) > 12
             THEN 'OVER LIMIT' ELSE 'ok' END AS flag
FROM        assets a
JOIN        obligors o ON o.obligor_id=a.obligor_id
JOIN        deals    d ON d.deal_id=a.deal_id
GROUP BY    d.deal_name, o.industry
ORDER BY    d.deal_name, SUM(a.par_amount) DESC;

-- ---------------------------------------------------------------------
-- 3.4  Top-10 obligor exposures per deal (single-obligor 2% cap)
-- ---------------------------------------------------------------------
WITH ranked AS (
    SELECT d.deal_name, o.obligor_name, o.moodys_rating, o.industry,
           SUM(a.par_amount) AS par,
           100.0*SUM(a.par_amount)/SUM(SUM(a.par_amount)) OVER (PARTITION BY d.deal_name) AS pct,
           ROW_NUMBER() OVER (PARTITION BY d.deal_name ORDER BY SUM(a.par_amount) DESC) AS rn
    FROM assets a
    JOIN obligors o ON o.obligor_id=a.obligor_id
    JOIN deals    d ON d.deal_id=a.deal_id
    GROUP BY d.deal_name, o.obligor_name, o.moodys_rating, o.industry
)
SELECT  deal_name, rn AS rank, obligor_name, moodys_rating, industry,
        printf('%,.0f', par) AS par, ROUND(pct,2) AS pct_of_deal,
        CASE WHEN pct>2 THEN 'OVER LIMIT' ELSE 'ok' END AS flag
FROM        ranked
WHERE       rn <= 10
ORDER BY    deal_name, rn;

-- ---------------------------------------------------------------------
-- 3.5  Defaulted-loan register with mark-to-market loss estimate
-- ---------------------------------------------------------------------
SELECT  d.deal_name, o.obligor_name, o.industry, a.facility_name,
        a.moodys_rating,
        printf('%,.0f', a.par_amount)                          AS par,
        a.market_price,
        printf('%,.0f', a.par_amount*(1-a.market_price/100.0)) AS est_loss
FROM        assets a
JOIN        obligors o ON o.obligor_id=a.obligor_id
JOIN        deals    d ON d.deal_id=a.deal_id
WHERE       a.is_defaulted=1
ORDER BY    a.par_amount*(1-a.market_price/100.0) DESC;

-- ---------------------------------------------------------------------
-- 3.6  Loan maturity profile — par maturing by year (reinvestment risk)
-- ---------------------------------------------------------------------
SELECT  d.deal_name,
        substr(a.maturity_date,1,4) AS maturity_year,
        COUNT(*)                    AS num_loans,
        printf('%,.0f', SUM(a.par_amount)) AS par_maturing
FROM        assets a
JOIN        deals d ON d.deal_id=a.deal_id
GROUP BY    d.deal_name, maturity_year
ORDER BY    d.deal_name, maturity_year;
