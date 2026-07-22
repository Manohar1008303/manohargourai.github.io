import pandas as pd
from utils.config_loader import ConfigLoader
from modules.loan_cashflow_engine import LoanCashflowEngine
from modules.pool_summary import PoolSummary
from modules.coverage_tests import CoverageTests
from modules.waterfall_engine import WaterfallEngine
from modules.reporting_engine import ReportingEngine

def main():
    print("=== CLO CASHFLOW ENGINE STARTED ===")

    config = ConfigLoader("data/waterfall_rules.json")
    benchmark = config.get_benchmark_rate()
    tranches = config.get_tranches()
    priority_order = config.get_payment_priority()
    oc_rules = config.get_oc_tests()
    ic_rules = config.get_ic_tests()
    trigger_logic = config.get_trigger_logic()
    loan_engine = LoanCashflowEngine("data/loan_data.xlsx")
    loan_engine.load_loans()
    loan_cf = loan_engine.calculate_cashflows()

    pool = PoolSummary(loan_cf)
    pool_summary = pool.compute_summary()

    tests = CoverageTests(pool_summary, tranches, oc_rules, ic_rules)
    test_results = tests.run_all_tests()

    waterfall = WaterfallEngine(
        pool_summary, tranches, priority_order, trigger_logic, test_results
    )
    waterfall_results = waterfall.run_waterfall()

    report = ReportingEngine()
    report.create_report(
        loan_df=loan_cf,
        pool_summary=pool_summary,
        test_results=test_results,
        waterfall_results=waterfall_results
    )

    print("=== CLO CASHFLOW ENGINE FINISHED ===")

if __name__ == "__main__":
    main()
