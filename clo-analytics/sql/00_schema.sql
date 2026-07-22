-- =====================================================================
--  CLO / Loan Syndication Analytics — Database Schema (SQLite)
--  Author: Manohar Gourai
--  Models a Collateralized Loan Obligation (CLO) servicing environment:
--  deals, liabilities (tranches), the underlying syndicated-loan
--  collateral pool, cash collections, the payment waterfall, indenture
--  compliance tests, and trustee-vs-internal reconciliation.
-- =====================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS trustee_positions;
DROP TABLE IF EXISTS compliance_tests;
DROP TABLE IF EXISTS distributions;
DROP TABLE IF EXISTS collections;
DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS obligors;
DROP TABLE IF EXISTS tranches;
DROP TABLE IF EXISTS deals;
DROP TABLE IF EXISTS rating_scale;

-- ---------------------------------------------------------------------
-- Reference: Moody's rating -> rating factor (used for WARF)
-- ---------------------------------------------------------------------
CREATE TABLE rating_scale (
    moodys_rating   TEXT PRIMARY KEY,
    rating_factor   INTEGER NOT NULL,   -- Moody's Rating Factor
    rank_order      INTEGER NOT NULL,   -- 1 = highest credit quality
    is_ccc          INTEGER NOT NULL    -- 1 if Caa1 or below
);

-- ---------------------------------------------------------------------
-- CLO deals (the securitisation vehicles / SPVs)
-- ---------------------------------------------------------------------
CREATE TABLE deals (
    deal_id             TEXT PRIMARY KEY,
    deal_name           TEXT NOT NULL,
    manager             TEXT NOT NULL,      -- collateral manager
    deal_type           TEXT NOT NULL,      -- 'Broadly Syndicated' | 'Middle Market'
    trustee             TEXT NOT NULL,
    currency            TEXT NOT NULL,
    closing_date        TEXT NOT NULL,
    reinvestment_end    TEXT NOT NULL,
    stated_maturity     TEXT NOT NULL,
    target_par          REAL NOT NULL       -- target collateral principal balance
);

-- ---------------------------------------------------------------------
-- Liabilities issued by each deal (rated debt tranches + equity)
-- ---------------------------------------------------------------------
CREATE TABLE tranches (
    tranche_id          TEXT PRIMARY KEY,
    deal_id             TEXT NOT NULL REFERENCES deals(deal_id),
    class_name          TEXT NOT NULL,      -- A, B, C, D, E, F, Sub
    moodys_rating       TEXT,               -- NULL for equity/sub notes
    seniority_rank      INTEGER NOT NULL,   -- 1 = most senior
    original_balance    REAL NOT NULL,
    current_balance     REAL NOT NULL,
    coupon_spread_bps   REAL,               -- spread over benchmark; NULL for equity
    is_deferrable       INTEGER NOT NULL,   -- PIK-able (typically C and below)
    oc_trigger_pct      REAL,               -- overcollateralisation trigger; NULL if none
    ic_trigger_pct      REAL                -- interest-coverage trigger; NULL if none
);

-- ---------------------------------------------------------------------
-- Obligors (borrowers whose loans sit in the collateral pool)
-- ---------------------------------------------------------------------
CREATE TABLE obligors (
    obligor_id          TEXT PRIMARY KEY,
    obligor_name        TEXT NOT NULL,
    industry            TEXT NOT NULL,      -- Moody's industry classification
    country             TEXT NOT NULL,
    moodys_rating       TEXT NOT NULL REFERENCES rating_scale(moodys_rating)
);

-- ---------------------------------------------------------------------
-- Assets = individual syndicated-loan positions held by a deal
-- ---------------------------------------------------------------------
CREATE TABLE assets (
    asset_id            TEXT PRIMARY KEY,
    deal_id             TEXT NOT NULL REFERENCES deals(deal_id),
    obligor_id          TEXT NOT NULL REFERENCES obligors(obligor_id),
    facility_name       TEXT NOT NULL,
    lien_type           TEXT NOT NULL,      -- 'First Lien' | 'Second Lien'
    par_amount          REAL NOT NULL,      -- internal book par (principal)
    market_price        REAL NOT NULL,      -- % of par (e.g. 99.25)
    coupon_spread_bps   REAL NOT NULL,      -- spread over base rate
    base_rate_pct       REAL NOT NULL,      -- reference rate (e.g. SOFR)
    purchase_date       TEXT NOT NULL,
    maturity_date       TEXT NOT NULL,
    moodys_rating       TEXT NOT NULL REFERENCES rating_scale(moodys_rating),
    is_defaulted        INTEGER NOT NULL,
    is_cov_lite         INTEGER NOT NULL
);

-- ---------------------------------------------------------------------
-- Cash collected by the deal each period (interest + principal)
-- ---------------------------------------------------------------------
CREATE TABLE collections (
    collection_id       INTEGER PRIMARY KEY,
    deal_id             TEXT NOT NULL REFERENCES deals(deal_id),
    period              TEXT NOT NULL,      -- e.g. '2025-Q1'
    payment_date        TEXT NOT NULL,
    interest_collections REAL NOT NULL,
    principal_collections REAL NOT NULL
);

-- ---------------------------------------------------------------------
-- Payment waterfall: what each tranche was paid each period
-- ---------------------------------------------------------------------
CREATE TABLE distributions (
    distribution_id     INTEGER PRIMARY KEY,
    deal_id             TEXT NOT NULL REFERENCES deals(deal_id),
    tranche_id          TEXT NOT NULL REFERENCES tranches(tranche_id),
    period              TEXT NOT NULL,
    payment_date        TEXT NOT NULL,
    waterfall_step      INTEGER NOT NULL,   -- priority order within the period
    interest_due        REAL NOT NULL,
    interest_paid       REAL NOT NULL,
    principal_paid      REAL NOT NULL,
    deferred_interest   REAL NOT NULL       -- PIK'd when cash insufficient
);

-- ---------------------------------------------------------------------
-- Indenture compliance tests run each period
-- ---------------------------------------------------------------------
CREATE TABLE compliance_tests (
    test_id             INTEGER PRIMARY KEY,
    deal_id             TEXT NOT NULL REFERENCES deals(deal_id),
    period              TEXT NOT NULL,
    test_category       TEXT NOT NULL,      -- 'Coverage' | 'Collateral Quality' | 'Concentration'
    test_name           TEXT NOT NULL,
    threshold_value     REAL NOT NULL,
    actual_value        REAL NOT NULL,
    threshold_type      TEXT NOT NULL,      -- 'min' (actual>=thr) | 'max' (actual<=thr)
    result              TEXT NOT NULL       -- 'PASS' | 'FAIL'
);

-- ---------------------------------------------------------------------
-- Trustee reconciliation: trustee-reported vs internal book positions
-- ---------------------------------------------------------------------
CREATE TABLE trustee_positions (
    recon_id            INTEGER PRIMARY KEY,
    deal_id             TEXT NOT NULL REFERENCES deals(deal_id),
    asset_id            TEXT NOT NULL REFERENCES assets(asset_id),
    as_of_date          TEXT NOT NULL,
    trustee_par         REAL NOT NULL,
    internal_par        REAL NOT NULL,
    break_amount        REAL NOT NULL,      -- trustee_par - internal_par
    break_type          TEXT NOT NULL,      -- 'Matched' | 'Position Break' | 'Missing at Trustee' | 'Missing Internally'
    age_days            INTEGER NOT NULL,
    status              TEXT NOT NULL       -- 'Matched' | 'Open' | 'Escalated' | 'Resolved'
);
