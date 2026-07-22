import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)

class CoverageTests:
    """
    Performs OC and IC coverage tests using:
    - Pool summary metrics
    - Tranche data from configuration
    """

    def __init__(self, pool_summary: dict, tranche_config: list, oc_rules: dict, ic_rules: dict):
        self.pool = pool_summary
        self.tranche_config = tranche_config
        self.oc_rules = oc_rules
        self.ic_rules = ic_rules

        self.results = {
            "OC": {},
            "IC": {},
            "Failed_OC": [],
            "Failed_IC": []
        }

    # -------------------------------------------------------------
    # Helper: get tranche balance given tranche name
    # -------------------------------------------------------------
    def _get_tranche_balance(self, name):
        for t in self.tranche_config:
            if t["Name"] == name:
                return t["Balance"]
        logger.error(f"Tranche balance not found for: {name}")
        return None

    # -------------------------------------------------------------
    # Helper: compute interest due for IC test
    # -------------------------------------------------------------
    def _get_interest_due(self, tranche):
        base = tranche["Spread"]
        sofr_rate = 0.0130  # From JSON BenchmarkRate
        return tranche["Balance"] * (sofr_rate + base)

    # -------------------------------------------------------------
    # OC Test Calculations
    # -------------------------------------------------------------
    def run_oc_tests(self):
        collateral = self.pool["Ending_Collateral"]

        for tranche_name, rules in self.oc_rules.items():
            tranche_balance = self._get_tranche_balance(tranche_name)
            if tranche_balance is None or tranche_balance == 0:
                continue

            oc_ratio = collateral / tranche_balance
            threshold = rules["Threshold"]

            self.results["OC"][tranche_name] = round(oc_ratio, 4)

            if oc_ratio < threshold:
                self.results["Failed_OC"].append(tranche_name)
                logger.warning(f"OC Test FAILED for {tranche_name}: {oc_ratio} < {threshold}")
            else:
                logger.info(f"OC Test PASSED for {tranche_name}: {oc_ratio} >= {threshold}")

    # -------------------------------------------------------------
    # IC Test Calculations
    # -------------------------------------------------------------
    def run_ic_tests(self):
        interest_available = self.pool["Total_Interest"]

        for tranche_name, rules in self.ic_rules.items():
            tranche = None

            for t in self.tranche_config:
                if t["Name"] == tranche_name:
                    tranche = t

            if tranche is None:
                logger.error(f"No tranche config found for IC Test: {tranche_name}")
                continue

            interest_due = self._get_interest_due(tranche)
            ic_ratio = interest_available / interest_due if interest_due > 0 else 0

            threshold = rules["Threshold"]

            self.results["IC"][tranche_name] = round(ic_ratio, 4)

            if ic_ratio < threshold:
                self.results["Failed_IC"].append(tranche_name)
                logger.warning(f"IC Test FAILED for {tranche_name}: {ic_ratio} < {threshold}")
            else:
                logger.info(f"IC Test PASSED for {tranche_name}: {ic_ratio} >= {threshold}")

    # -------------------------------------------------------------
    # Run All Tests
    # -------------------------------------------------------------
    def run_all_tests(self):
        logger.info("Running OC Tests...")
        self.run_oc_tests()

        logger.info("Running IC Tests...")
        self.run_ic_tests()

        logger.info("Coverage test calculations complete.")
        return self.results

