import os
import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)


class ReportingEngine:
    """
    Generates a multi-sheet Excel report of the entire CLO engine output.

    Sheets:
      - Loan Cashflows
      - Pool Summary
      - Coverage Tests (OC / IC, plus failed tests)
      - Waterfall Payments
      - Waterfall Shortfalls
      - Residual Equity
    """

    def __init__(self, output_path: str = "output/CLO_Waterfall_Report.xlsx"):
        self.output_path = output_path
        # Make sure output folder exists
        output_dir = os.path.dirname(output_path) or "."
        os.makedirs(output_dir, exist_ok=True)

    # ---------------------------------------------------------
    # Create the report
    # ---------------------------------------------------------
    def create_report(
        self,
        loan_df: pd.DataFrame,
        pool_summary: dict,
        test_results: dict,
        waterfall_results: dict,
    ):
        """
        Build a multi-sheet Excel workbook with all key results.
        """
        logger.info("Generating CLO Excel Report...")

        try:
            with pd.ExcelWriter(self.output_path, engine="xlsxwriter") as writer:
                # =====================================================
                # Sheet 1 – Loan Cashflows
                # =====================================================
                loan_df.to_excel(
                    writer,
                    sheet_name="Loan Cashflows",
                    index=False,
                )

                # =====================================================
                # Sheet 2 – Pool Summary
                # =====================================================
                pool_summary_df = pd.DataFrame([pool_summary])
                pool_summary_df.to_excel(
                    writer,
                    sheet_name="Pool Summary",
                    index=False,
                )

                # =====================================================
                # Sheet 3 – Coverage Tests
                # test_results structure:
                # {
                #   "OC": {tranche: ratio, ...},
                #   "IC": {tranche: ratio, ...},
                #   "Failed_OC": [ ... ],
                #   "Failed_IC": [ ... ]
                # }
                # =====================================================
                coverage_rows = []

                # OC ratios
                for tranche_name, ratio in test_results.get("OC", {}).items():
                    coverage_rows.append(
                        {
                            "TestType": "OC",
                            "Tranche": tranche_name,
                            "Ratio": ratio,
                        }
                    )

                # IC ratios
                for tranche_name, ratio in test_results.get("IC", {}).items():
                    coverage_rows.append(
                        {
                            "TestType": "IC",
                            "Tranche": tranche_name,
                            "Ratio": ratio,
                        }
                    )

                # Failed OC summary row
                failed_oc = test_results.get("Failed_OC", [])
                if failed_oc:
                    coverage_rows.append(
                        {
                            "TestType": "Failed_OC",
                            "Tranche": ", ".join(failed_oc),
                            "Ratio": "",
                        }
                    )

                # Failed IC summary row
                failed_ic = test_results.get("Failed_IC", [])
                if failed_ic:
                    coverage_rows.append(
                        {
                            "TestType": "Failed_IC",
                            "Tranche": ", ".join(failed_ic),
                            "Ratio": "",
                        }
                    )

                coverage_df = pd.DataFrame(coverage_rows)
                coverage_df.to_excel(
                    writer,
                    sheet_name="Coverage Tests",
                    index=False,
                )

                # =====================================================
                # Sheet 4 – Waterfall Payments
                # waterfall_results structure (from WaterfallEngine):
                # {
                #   "Payments":   {bucket: amount, ...},
                #   "Shortfalls": {bucket: amount, ...},
                #   "Residual_Equity": float
                # }
                # =====================================================
                payments_dict = waterfall_results.get("Payments", {})
                payments_df = pd.DataFrame(
                    [
                        {"Bucket": bucket, "Amount": amount}
                        for bucket, amount in payments_dict.items()
                    ]
                )
                payments_df.to_excel(
                    writer,
                    sheet_name="Waterfall Payments",
                    index=False,
                )

                # =====================================================
                # Sheet 5 – Waterfall Shortfalls
                # =====================================================
                shortfalls_dict = waterfall_results.get("Shortfalls", {})
                shortfalls_df = pd.DataFrame(
                    [
                        {"Bucket": bucket, "Shortfall": amount}
                        for bucket, amount in shortfalls_dict.items()
                    ]
                )
                shortfalls_df.to_excel(
                    writer,
                    sheet_name="Waterfall Shortfalls",
                    index=False,
                )

                # =====================================================
                # Sheet 6 – Residual Equity
                # =====================================================
                residual_equity = waterfall_results.get("Residual_Equity", 0)
                equity_df = pd.DataFrame(
                    [{"Residual_Equity": residual_equity}]
                )
                equity_df.to_excel(
                    writer,
                    sheet_name="Residual Equity",
                    index=False,
                )

            logger.info(
                f"CLO Excel report generated successfully at: {self.output_path}"
            )

        except Exception as e:
            logger.error(f"Error generating CLO Excel report: {e}")
            raise

