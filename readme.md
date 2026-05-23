# Expense Triage Agent

This project is a FastAPI + Streamlit expense triage system that categorizes transactions, flags anomalies, and generates a monthly summary.

## Execution Steps

### 1) Create and activate virtual environment

Windows (PowerShell):

```powershell
python -m venv env
env\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

### 3) Run backend API

```powershell
uvicorn app:app --reload
```

### 4) Run Streamlit frontend

Open a new terminal and run:

```powershell
streamlit run frontend/main.py
```

### 5) Run evaluation harness

```powershell
python tests/scenarios/test_harness.py
```

## API

- POST `/v1/triage`: Upload CSV + instruction. Returns ledger, anomalies, summary, and review candidates when needed.
- POST `/v1/triage/confirm`: Sends corrected categories and returns finalized ledger, anomalies, and summary.
- POST `/v1/triage/confirm/stream`: Streams confirm progress and final result using SSE.

## Notes

- LLM usage is optional and falls back gracefully if Ollama is unavailable.
- The human-review checkpoint is available in the Streamlit app for low-confidence items.

## Contact

- For issues while running the project: mangeshwayal4@gmail.com
