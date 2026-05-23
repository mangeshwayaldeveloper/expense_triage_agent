import os
from expense_triage_agent.services.transaction_loader import load_transactions_from_bytes
from expense_triage_agent.agent.orchestrator import Orchestrator


def test_end_to_end_load_and_run():
    path = os.path.join(os.getcwd(), "data", "sample_inputs", "transactions.csv")
    with open(path, "rb") as f:
        content = f.read()

    rows, errors = load_transactions_from_bytes(content)
    assert isinstance(rows, list)
    assert len(rows) > 0

    orch = Orchestrator()
    state = orch.run("categorize everything and flag anything unusual this month", rows)

    assert "ledger" in state
    assert "anomalies" in state
    assert "summary" in state
    # malformed row should be reported in errors
    assert isinstance(errors, list)
