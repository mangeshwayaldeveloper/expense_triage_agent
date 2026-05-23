import csv
import io
from typing import Tuple, List


def load_transactions_from_bytes(content: bytes) -> Tuple[List[dict], list[str]]:
    """Parse CSV content into rows and return malformed row notices.

    Returns (rows, errors)
    """
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    errors = []
    for i, row in enumerate(reader, start=1):
        try:
            # Basic validation: required columns
            if not row.get("transaction_id") or not row.get("amount") or not row.get("merchant"):
                errors.append(f"row {i}: missing required fields")
                continue
            # normalize amount
            amt = row.get("amount").strip()
            amt = amt.replace(',', '')
            row['amount'] = float(amt)
            rows.append(row)
        except Exception as e:
            errors.append(f"row {i}: malformed ({e})")
            continue
    return rows, errors
