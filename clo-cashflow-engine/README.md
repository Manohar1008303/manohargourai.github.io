# CLO Cashflow Engine

A modular Python engine that models Collateralized Loan Obligation (CLO) cashflows end to end.
It loads loan-level data, builds a pool summary, runs OC and IC coverage tests, and executes
the payment waterfall across tranches based on configurable trigger logic, then generates a
structured report of the results.

## Tech
Python · Pandas · Structured Finance · Waterfall Modeling

## Structure
- `main.py` — entry point that runs the full engine
- `modules/` — pool summary, loan cashflow, coverage tests, waterfall, and reporting logic
- `utils/` — config loading and logging helpers
- `data/waterfall_rules.json` — configurable benchmark, fees, tranches, and trigger rules
- `test_run.py` — sample run

## Notes
Uses synthetic sample data for demonstration. The input workbook (`data/loan_data.xlsx`)
and generated report (`output/CLO_Waterfall_Report.xlsx`) are produced/consumed at runtime.

## Run
```bash
python main.py
```
