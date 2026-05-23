from pydantic import BaseModel,Field

class Transaction(BaseModel):
    transaction_id: str
    date: str
    merchant: str
    description: str | None = ""
    amount: float
    currency: str = "EUR"
    account: str


class CategorizedTransaction(Transaction):
    category: str
    confidence: float = Field(ge=0.0, le=1.0)


class Anomaly(BaseModel):
    transaction_id: str
    merchant: str
    reason: str
    severity: str = "medium"


class MonthlySummary(BaseModel):
    total_by_category: dict[str, float]
    anomaly_count: int
    narrative: str