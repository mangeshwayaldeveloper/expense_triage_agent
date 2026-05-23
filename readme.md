# Expense Triage Agent — Minimal Implementation

This repository contains a minimal FastAPI-based expense triage agent with deterministic tools and a simple orchestrator.

Quick start

instructions are for windows, please check the instruction for
mac os to activate and create virtual environment

```
create a virtual env
python -m venv env

activate the virtual env

env\scripts\activate

pip install -r requirements.txt


uvicorn app:app --reload


API

- POST `/v1/triage` — multipart form: `file` CSV and optional 
`instruction` string. Returns a JSON state including `review_needed` and `review_candidates` when low confidence items are present.
- POST `/v1/triage/confirm` — JSON body with `ledger` (the original parsed rows) and `corrections` mapping `transaction_id` -> `category`. Returns final `ledger`, `anomalies`, and `summary`.

Design notes

- Deterministic rules are in `src/expense_triage_agent/tools`.
- An LLM wrapper is in `src/expense_triage_agent/llm/ollama_client.py` but LLM calls are optional by default.
- The orchestrator implements the planner and tool routing.

What I'd add with more time

- LangGraph orchestration for visualizing nodes and pauses.
- A web UI for the human-review checkpoint.
- A richer evaluation harness with 8-10 deterministic scenarios and a `make test` runner.

- To Check the output
- run the streamlit file by below command
- streamlit run frontend/main.py


- if any query or issue in running the file please contact me
- mangeshwayal4@gmail.com
