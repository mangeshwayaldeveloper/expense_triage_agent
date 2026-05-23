from typing import TypedDict
from ..domain.models import Anomaly, CategorizedTransaction, MonthlySummary


class AgentState(TypedDict, total=False):
    instruction: str
    transactions: list[dict]
    ledger: list[CategorizedTransaction]
    anomalies: list[Anomaly]
    summary: MonthlySummary
    review_needed: bool