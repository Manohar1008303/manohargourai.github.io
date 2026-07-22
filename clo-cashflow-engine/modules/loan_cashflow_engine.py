import pandas as pd
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)


class LoanCashflowEngine:
    """
    Computes quarterly loan-level cashflows for each loan in the portfolio.
    Includes interest, scheduled principal, prepayments, defaults,
    recoveries, and ending balances.
    """

    def __init__(self, loan_file_path: str):
        self.loan_file_path = loan_file_path
        self.loans_df = None

    # -----------------------------------------------
    # Load Data
    # -----------------------------------------------
    def load_loans(self):
        try:
            self.loans_df = pd.read_excel(self.loan_file_path)
            logger.info(f"Loaded loan data ({len(self.loans_df)} loans).")
        except Exception as e:
            logger.error(f"Error loading loan file: {e}")
            raise e

    # -----------------------------------------------
    # Core Cashflow Calculations
    # -----------------------------------------------
    def calculate_cashflows(self):
        if self.loans_df is None:
            raise ValueError("Loan data not loaded. Call load_loans() first.")

        df = self.loans_df.copy()

        logger.info("Starting cashflow calculations...")

        # Interest = Balance × TotalRate × Days / 360
        df["Interest_Calc"] = (
            df["Balance"] * (df["TotalRate_%"] / 100) * df["Days"] / 360
        ).round(2)

        # Total principal received
        df["Total_Principal"] = df["Scheduled_Principal"] + df["Prepayment"]

        # Default losses + recoveries
        df["Default_Loss"] = np.where(
            df["DefaultFlag"] == 1,
            df["Balance"] * (1 - df["RecoveryRate"]),
            0
        ).round(2)

        df["Recovery_Amount"] = np.where(
            df["DefaultFlag"] == 1,
            df["Balance"] * df["RecoveryRate"],
            0
        ).round(2)

        # Ending balance
        df["Ending_Balance"] = (
            df["Balance"]
            - df["Total_Principal"]
            - df["Default_Loss"]
        ).clip(lower=0).round(2)

        logger.info("Loan cashflow calculations completed.")

        self.loans_df = df
        return df

    # -----------------------------------------------
    # Get Final Cashflow Output
    # -----------------------------------------------
    def get_cashflows(self):
        if self.loans_df is None:
            logger.error("Cashflows not calculated. Call calculate_cashflows().")
            raise ValueError("Cashflows not calculated.")
        return self.loans_df
