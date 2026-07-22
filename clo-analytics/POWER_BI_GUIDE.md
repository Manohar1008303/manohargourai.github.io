# Power BI Guide — CLO Analytics

The interactive `dashboard.html` demonstrates the visuals, but the project is
designed to load natively into **Power BI** (which is on the CV). This guide
shows how to rebuild the same dashboard in Power BI from the CSVs in `data/`.

## 1. Load the data

`Get Data → Text/CSV` and import all nine files from `data/`:

`rating_scale, deals, tranches, obligors, assets, collections, distributions, compliance_tests, trustee_positions`

(Alternatively, `Get Data → ODBC / SQLite` against `clo.sqlite`, which also
exposes the four reporting views.)

## 2. Star schema / model relationships

The model is a classic star. `assets`, `distributions`, `collections`,
`compliance_tests` and `trustee_positions` are fact tables; `deals`,
`tranches`, `obligors` and `rating_scale` are dimensions.

| From (fact)              | Column      | To (dimension)  | Column        | Cardinality |
|--------------------------|-------------|-----------------|---------------|-------------|
| assets                   | deal_id     | deals           | deal_id       | many-to-one |
| assets                   | obligor_id  | obligors        | obligor_id    | many-to-one |
| assets                   | moodys_rating | rating_scale  | moodys_rating | many-to-one |
| tranches                 | deal_id     | deals           | deal_id       | many-to-one |
| distributions            | tranche_id  | tranches        | tranche_id    | many-to-one |
| distributions            | deal_id     | deals           | deal_id       | many-to-one |
| collections              | deal_id     | deals           | deal_id       | many-to-one |
| compliance_tests         | deal_id     | deals           | deal_id       | many-to-one |
| trustee_positions        | asset_id    | assets          | asset_id      | many-to-one |

Mark `deals` as the primary filter dimension and add a slicer on `deal_name`.

## 3. Core DAX measures

```DAX
Collateral Par        = SUM ( assets[par_amount] )

WARF =
DIVIDE (
    SUMX ( FILTER ( assets, assets[is_defaulted] = 0 ),
           RELATED ( rating_scale[rating_factor] ) * assets[par_amount] ),
    SUMX ( FILTER ( assets, assets[is_defaulted] = 0 ), assets[par_amount] )
)

WAS (bps) =
DIVIDE (
    SUMX ( assets, assets[coupon_spread_bps] * assets[par_amount] ),
    SUM ( assets[par_amount] )
)

CCC % =
DIVIDE (
    SUMX ( FILTER ( assets, RELATED ( rating_scale[is_ccc] ) = 1 ), assets[par_amount] ),
    SUM ( assets[par_amount] )
)

Compliance Pass Rate =
DIVIDE (
    CALCULATE ( COUNTROWS ( compliance_tests ), compliance_tests[result] = "PASS" ),
    COUNTROWS ( compliance_tests )
)

Trustee Match Rate =
DIVIDE (
    CALCULATE ( COUNTROWS ( trustee_positions ), trustee_positions[break_type] = "Matched" ),
    COUNTROWS ( trustee_positions )
)

Gross Break Exposure = SUMX ( trustee_positions, ABS ( trustee_positions[break_amount] ) )

OC Cushion (pp) =                       -- for coverage tests only
CALCULATE (
    SUMX ( compliance_tests, compliance_tests[actual_value] - compliance_tests[threshold_value] ),
    compliance_tests[test_category] = "Coverage"
)
```

## 4. Suggested report pages (mirrors dashboard.html)

1. **Overview** — KPI cards (Collateral Par, WARF, Pass Rate, Match Rate),
   par-by-deal bar, pass/fail donut.
2. **Compliance** — matrix of tests with conditional formatting on `result`
   (red = FAIL), OC-cushion line chart by period, deal slicer.
3. **Waterfall** — stacked bar of interest paid vs deferred by tranche;
   equity-yield line by period.
4. **Portfolio** — par-weighted rating column chart, industry bar, top-obligor
   table with a 2% single-obligor reference line.
5. **Reconciliation** — break-type donut, aged-break column chart, escalation
   table filtered to `status = "Escalated"`.

## 5. Conditional formatting cues
- `result = "FAIL"` → red background.
- `cushion < 0` → red text (breach); small positive cushion → amber (watch).
- `age_days > 15` → red (past escalation SLA).
