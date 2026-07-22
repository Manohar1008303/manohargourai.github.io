import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)

class PoolSummary:
    """
    Aggregates loan-level cashflows into pool-level metrics.
    Provides total interest, principal, recoveries, collateral,
    and weighted-average portfolio statistics.
    """

    def __init__(self, loans_df: pd.DataFrame):
        self.df = loans_df
        self.summary = {}

    # -----------------------------------------------
    # Compute Pool Summary
    # -----------------------------------------------
    def compute_summary(self):
        logger.info("Computing pool summary...")

        df = self.df

        # Total cashflows
        total_interest = df["Interest_Calc"].sum()
        total_principal = df["Total_Principal"].sum()
        total_recovery = df["Recovery_Amount"].sum()
        default_losses = df["Default_Loss"].sum()

        # Ending collateral balance
        ending_collateral = df["Ending_Balance"].sum()

        # Weighted average spread
        df["Weight"] = df["Balance"] / df["Balance"].sum()
        wa_spread = (df["Spread_%"] * df["Weight"]).sum()

        # Weighted average life
        wa_life = (df["WAL"] * df["Weight"]).sum()

        # Rating distribution
        rating_dist = df["Rating"].value_counts().to_dict()

        # Save final summary
        self.summary = {
            "Total_Interest": round(total_interest, 2),
            "Total_Principal": round(total_principal, 2),
            "Total_Recovery": round(total_recovery, 2),
            "Default_Losses": round(default_losses, 2),
            "Ending_Collateral": round(ending_collateral, 2),
            "Weighted_Avg_Spread": round(wa_spread, 3),
            "Weighted_Avg_Life": round(wa_life, 2),
            "Rating_Distribution": rating_dist,
            "Available_Interest_Cash": round(total_interest + total_recovery, 2),
            "Available_Principal_Cash": round(total_principal, 2),
            "Total_Available_Cash": round(total_interest + total_recovery + total_principal, 2)
        }

        logger.info("Pool summary computed successfully.")

        return self.summary

    # -----------------------------------------------
    # Getter
    # -----------------------------------------------
    def get_summary(self):
        if not self.summary:
            logger.warning("Pool summary requested before computation.")
        return self.summary
