from statistics import mean
from ..domain.models import Anomaly, CategorizedTransaction


def detect_anomalies(ledger: list[CategorizedTransaction]) -> list[Anomaly]:
    clean_rows = [row for row in ledger if row.merchant.strip() and row.amount is not None]
    if not clean_rows:
        return []

    anomalies: list[Anomaly] = []
    seen = set()
    category_amounts: dict[str, list[float]] = {}

    for row in clean_rows:
        key = (row.date, row.merchant.lower(), row.amount)
        if key in seen:
            anomalies.append(
                Anomaly(
                    transaction_id=row.transaction_id,
                    merchant=row.merchant,
                    reason="possible duplicate charge",
                    severity="high",
                )
            )
        seen.add(key)
        category_amounts.setdefault(row.category, []).append(abs(row.amount))

    for row in clean_rows:
        values = category_amounts.get(row.category, [])
        if len(values) >= 3:
            avg = mean(values)
            if abs(row.amount) > avg * 3:
                anomalies.append(
                    Anomaly(
                        transaction_id=row.transaction_id,
                        merchant=row.merchant,
                        reason="outlier spend for category",
                        severity="high",
                    )
                )

        if row.merchant.lower().startswith("lyf*"):
            anomalies.append(
                Anomaly(
                    transaction_id=row.transaction_id,
                    merchant=row.merchant,
                    reason="ambiguous payment processor merchant",
                    severity="medium",
                )
            )

    return anomalies