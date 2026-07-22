-- =====================================================================
--  02 — PAYMENT WATERFALL / PRIORITY OF PAYMENTS
--  How each period's interest collections cascade down the tranches,
--  senior to subordinated, with any deferred (PIK) interest, and what
--  residual flows to the equity / subordinated notes.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 2.1  Full interest waterfall for the latest period, in priority order
-- ---------------------------------------------------------------------
WITH latest AS (
    SELECT deal_id, MAX(period) AS period FROM distributions GROUP BY deal_id
)
SELECT  d.deal_name,
        dist.period,
        dist.waterfall_step        AS step,
        t.class_name,
        t.moodys_rating,
        printf('%,.0f', dist.interest_due)      AS interest_due,
        printf('%,.0f', dist.interest_paid)     AS interest_paid,
        printf('%,.0f', dist.deferred_interest) AS deferred_pik
FROM        distributions dist
JOIN        latest l ON l.deal_id=dist.deal_id AND l.period=dist.period
JOIN        tranches t ON t.tranche_id=dist.tranche_id
JOIN        deals d ON d.deal_id=dist.deal_id
ORDER BY    d.deal_name, dist.waterfall_step;

-- ---------------------------------------------------------------------
-- 2.2  Waterfall reconciliation — does cash in = cash out each period?
--      Interest collections should equal senior fees + all interest paid
--      + residual to equity. Validates the waterfall model end-to-end.
-- ---------------------------------------------------------------------
WITH paid AS (
    SELECT dist.deal_id AS deal_id, dist.period AS period,
           SUM(CASE WHEN t.class_name<>'Sub' THEN dist.interest_paid ELSE 0 END) AS debt_interest_paid,
           SUM(CASE WHEN t.class_name ='Sub' THEN dist.interest_paid ELSE 0 END) AS equity_residual
    FROM distributions dist
    JOIN tranches t ON t.tranche_id=dist.tranche_id
    GROUP BY dist.deal_id, dist.period
)
SELECT  d.deal_name, c.period,
        printf('%,.0f', c.interest_collections)  AS interest_collected,
        printf('%,.0f', p.debt_interest_paid)    AS debt_interest_paid,
        printf('%,.0f', p.equity_residual)       AS equity_residual,
        -- implied senior fees = collections - debt interest - equity residual
        printf('%,.0f', c.interest_collections - p.debt_interest_paid - p.equity_residual) AS senior_fees_and_expenses
FROM        collections c
JOIN        paid p ON p.deal_id=c.deal_id AND p.period=c.period
JOIN        deals d ON d.deal_id=c.deal_id
ORDER BY    d.deal_name, c.period;

-- ---------------------------------------------------------------------
-- 2.3  Deferred (PIK) interest watch — deferrable tranches not paid in full
-- ---------------------------------------------------------------------
SELECT  d.deal_name, dist.period, t.class_name, t.moodys_rating,
        printf('%,.0f', dist.interest_due)       AS interest_due,
        printf('%,.0f', dist.interest_paid)      AS interest_paid,
        printf('%,.0f', dist.deferred_interest)  AS deferred_pik
FROM        distributions dist
JOIN        tranches t ON t.tranche_id=dist.tranche_id
JOIN        deals    d ON d.deal_id=dist.deal_id
WHERE       dist.deferred_interest > 0
ORDER BY    dist.deferred_interest DESC;

-- ---------------------------------------------------------------------
-- 2.4  Equity distribution trend — cash-on-cash to the subordinated notes
--      Residual to equity as an annualised % of the sub-note balance.
-- ---------------------------------------------------------------------
SELECT  d.deal_name, dist.period,
        printf('%,.0f', dist.interest_paid)                         AS equity_distribution,
        printf('%,.0f', t.current_balance)                          AS sub_note_balance,
        ROUND(100.0 * dist.interest_paid / t.current_balance * 4, 2) AS annualised_yield_pct
FROM        distributions dist
JOIN        tranches t ON t.tranche_id=dist.tranche_id AND t.class_name='Sub'
JOIN        deals    d ON d.deal_id=dist.deal_id
ORDER BY    d.deal_name, dist.period;

-- ---------------------------------------------------------------------
-- 2.5  Tranche cost of funding — weighted average liability spread
-- ---------------------------------------------------------------------
SELECT  d.deal_name,
        ROUND(SUM(t.coupon_spread_bps*t.current_balance)
              / SUM(CASE WHEN t.coupon_spread_bps IS NOT NULL THEN t.current_balance END), 1)
              AS wavg_liability_spread_bps
FROM        tranches t
JOIN        deals d ON d.deal_id=t.deal_id
WHERE       t.coupon_spread_bps IS NOT NULL
GROUP BY    d.deal_name;
