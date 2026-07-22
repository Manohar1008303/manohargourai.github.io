import pandas as pd

from utils.config_loader import ConfigLoader
from modules.loan_cashflow_engine import LoanCashflowEngine
from modules.pool_summary import PoolSummary
from modules.coverage_tests import CoverageTests
from modules.waterfall_engine import WaterfallEngine
from modules.reporting_engine import ReportingEngine

from utils.logger import get_logger

logger = get_logger(__name__)


def main():

    logger.info("=== CLO CASHFLOW ENGINE STARTED ===")

    # ---------------------------------------------------------
    # 1. Load Configuration JSON
    # ---------------------------------------------------------
    config = ConfigLoader("data/waterfall_rules.json")

    benchmark = config.get_benchmark_rate()
    tranches = config.get_tranches()
    priority_order = config.get_payment_priority()
    oc_rules = config.get_oc_tests()
    ic_rules = config.get_ic_tests()
    trigger_logic = config.get_trigger_logic()

    logger.info("Configuration loaded successfully.")

    # ---------------------------------------------------------
    # 2. Load Loan Data & Calculate Cashflows
    # ---------------------------------------------------------
    loan_engine = LoanCashflowEngine("data/loan_data.xlsx")
    loan_engine.load_loans()
    loan_cf = loan_engine.calculate_cashflows()

    logger.info("Loan cashflows calculated.")

    # ---------------------------------------------------------
    # 3. Compute Pool Summary
    # ---------------------------------------------------------
    pool = PoolSummary(loan_cf)
    pool_summary = pool.compute_summary()

    logger.info("Pool summary created.")

    # ---------------------------------------------------------
    # 4. Run Coverage Tests
    # ---------------------------------------------------------
    tests = CoverageTests(
        pool_summary,
        tranches,
        oc_rules,
        ic_rules
    )

    test_results = tests.run_all_tests()

    logger.info("Coverage tests completed.")

    # ---------------------------------------------------------
    # 5. Execute Waterfall Engine
    # ---------------------------------------------------------
    waterfall = WaterfallEngine(
        pool_summary,
        tranches,
        priority_order,
        trigger_logic,
        test_results
    )

    waterfall_results = waterfall.run_waterfall()

    logger.info("Waterfall execution completed.")

    # ---------------------------------------------------------
    # 6. Generate Final Excel Report
    # ---------------------------------------------------------
    report = ReportingEngine()
    report.create_report(
        loan_df=loan_cf,
        pool_summary=pool_summary,
        test_results=test_results,
        waterfall_results=waterfall_results
    )

    logger.info("Excel report generated successfully.")

    logger.info("=== CLO CASHFLOW ENGINE FINISHED ===")


if __name__ == "__main__":
    main()
