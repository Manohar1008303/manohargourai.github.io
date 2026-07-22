# CLO Analytics — SQL + BI Portfolio Project

**Author:** Manohar Gourai
**Domain:** Loan syndication · Collateralized Loan Obligations (CLO / CDO) · structured-finance servicing
**Stack:** SQLite (SQL) · Python (synthetic data) · Power BI / interactive HTML dashboard

A self-contained analytics project that models the day-to-day work of a CLO
compliance and loan-operations team: monitoring indenture compliance tests,
running the payment waterfall, analysing the syndicated-loan collateral pool,
and reconciling trustee-reported positions against internal books. It's built
on realistic **synthetic** data — no confidential information — so it can be
shared openly on a portfolio or GitHub.

## Why this project

It mirrors the exact functions on my CV at BNY — trustee reconciliation,
indenture compliance monitoring, hypothetical trade / coverage-test analysis,
quarterly investor-report and waterfall reviews — and expresses them in SQL and
BI, the analytics skills I'm building in my MS in Business Analytics.

## Featured client — Golub Capital

The project centres on **Golub Capital Partners CLO 2024-1**, a middle-market
CLO and the largest deal in the book (~$653M collateral, 215 loans). Golub is
one of the portfolios I supported at BNY, so it's the deal I know best. It's the
flagship throughout: pre-selected in the dashboard's deal filters, and given its
own single-client "client 360" analysis in `sql/06_golub_focus.sql` (deal
profile, tranche stack, compliance scorecard, waterfall, top exposures, and
reconciliation — the way a lead analyst would prep a client review pack).

## What's in the data

Four CLOs — **Golub Capital** (featured), Carlyle, ARES and Bain Capital —
trustee'd by BNY, each with a full capital structure and collateral pool:

| Metric | Value |
|---|---|
| CLO deals | 4 (2 broadly syndicated, 2 middle market) |
| Featured deal | Golub Capital Partners CLO 2024-1 (~$653M, 215 loans) |
| Syndicated loans | 700 across 300 obligors |
| Collateral par | ~$2.01 billion |
| Tranches | 28 (Class A→F + subordinated notes per deal) |
| Periods | 4 quarterly payment dates |
| Compliance tests run | 240 (9 period-level breaches — realistic watch items) |
| Trustee positions reconciled | 700 (86 breaks, ~88% match rate, 40 escalated) |

## The four analytical angles

1. **CLO indenture compliance** (`sql/01_compliance_tests.sql`) — overcollateralisation
   (OC) and interest-coverage (IC) tests per tranche, collateral-quality tests
   (WARF, weighted-average spread) and concentration limits (single obligor,
   single industry, Caa/CCC bucket, second-lien, defaults). Includes a
   pass/fail scorecard, an exceptions worklist, a cushion **trend** for early
   warning, and an independent WARF recomputation straight from the loan tape as
   a control check.
2. **Payment waterfall** (`sql/02_payment_waterfall.sql`) — the priority of
   payments: interest cascading senior→subordinated, deferred (PIK) interest on
   junior tranches, residual to equity, an end-to-end cash-in = cash-out
   reconciliation, and equity cash-on-cash yield.
3. **Portfolio & credit analytics** (`sql/03_portfolio_analytics.sql`) — pool
   composition, par-weighted rating distribution, industry and obligor
   concentration vs limits, a defaulted-loan register with mark-to-market loss
   estimates, and a maturity profile.
4. **Trustee reconciliation** (`sql/04_trustee_reconciliation.sql`) — trustee vs
   internal par, break classification (position break, missing at trustee,
   missing internally), aged-break bucketing against a 15-day escalation SLA,
   and the escalation worklist ranked by exposure.

`sql/05_views.sql` creates four reporting views (`v_portfolio_summary`,
`v_compliance_scorecard`, `v_recon_summary`, `v_asset_detail`) for BI tools.
`sql/06_golub_focus.sql` is the featured-client deep dive on Golub Capital.

## Data model (star schema)

```
                 rating_scale        deals
                      |               |  \
   obligors ---- assets ---- tranches |   collections
                 |   |          |     |
     trustee_positions       distributions
                              compliance_tests
```

Fact tables: `assets`, `distributions`, `collections`, `compliance_tests`,
`trustee_positions`. Dimensions: `deals`, `tranches`, `obligors`,
`rating_scale`. Full DDL in `sql/00_schema.sql`.

## How to run it

```bash
# 1. (Re)build the database and CSVs from scratch — deterministic (seed=42)
python3 generate_data.py            # creates clo.sqlite + data/*.csv

# 2. Run any analysis
sqlite3 clo.sqlite < sql/01_compliance_tests.sql

# 3. Rebuild the dashboard data (optional; dashboard.html already includes it)
python3 build_dashboard.py
```

## Deliverables

| File | What it is |
|---|---|
| `clo.sqlite` | The loaded database (8 tables + 4 views) — **query this** |
| `data/*.csv` | The nine raw tables, for Power BI / Excel / Tableau import |
| `sql/00–06` | Schema, four analysis scripts, reporting views, and the Golub client 360 |
| `dashboard.html` | Interactive BI dashboard (open in any browser) |
| `POWER_BI_GUIDE.md` | Star-schema relationships + DAX to rebuild it in Power BI |
| `generate_data.py` | The synthetic-data engine |

## How it maps to my CV

| CV responsibility (BNY) | In this project |
|---|---|
| Trustee reconciliation | `sql/04` + reconciliation dashboard tab |
| Indenture compliance monitoring | `sql/01` OC/IC, quality & concentration tests |
| Hypothetical trade / coverage-test analysis | OC/IC cushion and WARF recomputation logic |
| Quarterly investor report & waterfall reviews | `sql/02` waterfall + cash-in=cash-out check |
| Power BI dashboards for portfolio oversight | `dashboard.html` + `POWER_BI_GUIDE.md` |
| Aged-break resolution & escalation | Aged-break buckets + escalation worklist |
| Golub Capital (portfolio supported at BNY) | Featured deal + `sql/06` client 360 |

## Notes
- All data is synthetic and generated locally; any resemblance to real deals is
  coincidental. Manager and trustee names are used only to make the scenario
  concrete and reflect the portfolios listed on my CV.
- Methodology (rating factors, OC/IC formulas, WARF) follows standard CLO market
  conventions but is simplified for a portfolio demonstration.
- The repo also contains build intermediates (`build_dashboard.py`,
  `dashboard_template.html`, `_dashboard_data.json`) and an empty `clo.db`
  placeholder; the authoritative database is **`clo.sqlite`**.
