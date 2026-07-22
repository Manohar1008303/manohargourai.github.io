from utils.logger import get_logger

logger = get_logger(__name__)

class WaterfallEngine:
    """
    Executes the CLO payment waterfall:
    1. Pays fees
    2. Pays tranches by seniority
    3. Applies trigger-based redirection (OC/IC failures)
    4. Sends residual cash to equity
    """

    def __init__(self, pool_summary, tranche_config, priority_order, trigger_logic, coverage_results):
        self.pool = pool_summary
        self.tranches = tranche_config
        self.priority_order = priority_order
        self.trigger_logic = trigger_logic
        self.coverage = coverage_results

        # Starting cash buckets
        self.interest_cash = self.pool["Available_Interest_Cash"]
        self.principal_cash = self.pool["Available_Principal_Cash"]
        self.total_cash = self.pool["Total_Available_Cash"]

        # Payment results
        self.results = {
            "Payments": {},
            "Shortfalls": {},
            "Residual_Equity": 0
        }

    # -----------------------------------------------------
    # Helper: apply payment to a specific obligation
    # -----------------------------------------------------
    def _apply_payment(self, name, amount_due):
        """
        Pays the given amount from total available cash.
        Records shortfall if cash is insufficient.
        """

        if self.total_cash <= 0:
            # total shortfall
            self.results["Payments"][name] = 0
            self.results["Shortfalls"][name] = amount_due
            logger.warning(f"SHORTFALL — No cash available for {name}.")
            return

        payment = min(self.total_cash, amount_due)
        self.total_cash -= payment

        self.results["Payments"][name] = round(payment, 2)

        if payment < amount_due:
            self.results["Shortfalls"][name] = round(amount_due - payment, 2)
            logger.warning(f"SHORTFALL — {name}: Paid {payment}, Shortfall {amount_due - payment}.")
        else:
            logger.info(f"Paid {name}: {payment}")

    # -----------------------------------------------------
    # Helper: derive interest due for a tranche
    # -----------------------------------------------------
    def _interest_due(self, tranche):
        sofr = 0.0130  # quarterly SOFR rate
        return tranche["Balance"] * (sofr + tranche["Spread"])

    # -----------------------------------------------------
    # Trigger processing logic
    # -----------------------------------------------------
    def _apply_triggers(self):
        suspend = set()

        # OC failures → suspend list
        if self.coverage["Failed_OC"]:
            suspend.update(self.trigger_logic["If_OC_Fails"]["SuspendPaymentsTo"])
            logger.warning(f"OC FAILURE — Suspending payments to: {suspend}")

        # IC failures → suspend list
        if self.coverage["Failed_IC"]:
            suspend.update(self.trigger_logic["If_IC_Fails"]["SuspendPaymentsTo"])
            logger.warning(f"IC FAILURE — Additional suspensions: {suspend}")

        return suspend

    # -----------------------------------------------------
    # Main Waterfall Execution
    # -----------------------------------------------------
    def run_waterfall(self):
        logger.info("Starting CLO Waterfall Execution...")

        suspended = self._apply_triggers()

        for step in self.priority_order:
            logger.info(f"Processing step: {step}")

            # 1. Fee payments
            if step.startswith("Fees."):
                fee_key = step.split(".")[1]
                amount = 0

                # Look up fee amount from JSON
                if fee_key == "SeniorExpenses":
                    amount = 150000
                elif fee_key == "TrusteeFees":
                    amount = 50000

                self._apply_payment(f"Fee_{fee_key}", amount)
                continue

            # 2. Tranche interest payments
            if step.startswith("Tranches."):
                tranche_name = step.split(".")[1]

                # Skip if suspended by tests
                if tranche_name in suspended:
                    logger.warning(f"Skipping {tranche_name} due to trigger suspension.")
                    continue

                tranche = next((t for t in self.tranches if t["Name"] == tranche_name), None)
                if tranche is None:
                    logger.error(f"Tranche {tranche_name} not found in configuration.")
                    continue

                interest_due = self._interest_due(tranche)
                self._apply_payment(f"{tranche_name}_Interest", interest_due)
                continue

        # 3. Equity residual gets remaining cash
        self.results["Residual_Equity"] = round(self.total_cash, 2)
        logger.info(f"Equity Receives Residual Cash: {self.total_cash}")

        self.total_cash = 0
        return self.results
