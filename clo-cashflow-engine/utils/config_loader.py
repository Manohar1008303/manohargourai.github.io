import json
from utils.logger import get_logger

logger = get_logger(__name__)

class ConfigLoader:
    """
    Loads and manages all CLO waterfall configuration rules
    from waterfall_rules.json.

    This includes:
    - Benchmark rate
    - Fee structure
    - Tranche data
    - Coverage tests (OC/IC)
    - Payment priority
    - Trigger logic
    """

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = None
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, "r") as f:
                self.config = json.load(f)
            logger.info(f"Loaded configuration from {self.config_path}")

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise e

    # -----------------------------
    # Access helper methods
    # -----------------------------

    def get_benchmark_rate(self):
        return self.config.get("BenchmarkRate", {})

    def get_fees(self):
        return self.config.get("Fees", {})

    def get_tranches(self):
        return self.config.get("Tranches", [])

    def get_tranche_names(self):
        """Returns list of tranche names in priority order."""
        return [t["Name"] for t in self.get_tranches()]

    def get_payment_priority(self):
        return self.config.get("PaymentPriority", [])

    def get_oc_tests(self):
        return self.config.get("CoverageTests", {}).get("OC", {})

    def get_ic_tests(self):
        return self.config.get("CoverageTests", {}).get("IC", {})

    def get_trigger_logic(self):
        return self.config.get("TriggerLogic", {})

    def get_tranche_by_name(self, name: str):
        for t in self.get_tranches():
            if t["Name"] == name:
                return t
        logger.error(f"Tranche not found: {name}")
        return None
