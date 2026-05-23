from expense_triage_agent.services.transaction_loader import load_transactions_from_bytes
from expense_triage_agent.agent.orchestrator import Orchestrator
import os


def main():
    csv_path = os.path.join(os.getcwd(), "data", "sample_inputs", "transactions.csv")
    print("Loading:", csv_path)
    with open(csv_path, "rb") as f:
        content = f.read()
    rows, errors = load_transactions_from_bytes(content)
    print(f"Loaded {len(rows)} rows, {len(errors)} errors")
    orch = Orchestrator()
    state = orch.run("categorize everything and flag anything unusual this month", rows)
    print("Review needed:", state.get("review_needed"))
    if state.get("review_needed"):
        print("Review candidates:")
        for r in state.get("ledger"):
            if r.confidence < orch.settings.TEMPERATURE:
                print(r.transaction_id, r.merchant, r.amount, r.category, r.confidence)
    print("Anomalies:")
    for a in state.get("anomalies", []):
        print(a.transaction_id, a.merchant, a.reason, a.severity)
    print("Summary:")
    print(state.get("summary").model_dump())


if __name__ == "__main__":
    main()
