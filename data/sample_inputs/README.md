# Expense Triage Agent — Materials Pack

This folder contains everything you need for the take-home. Read the main brief (`Expense_Triage_Agent_TakeHome.docx`) first; the files here are the inputs that brief refers to.

## Files

| File | Description |
|---|---|
| `transactions.csv` | One month (~128 rows) of EUR transactions. Your agent processes this. |
| `DATA_DICTIONARY.md` | Column-by-column description of `transactions.csv`. Read this first. |

## A few notes

- The CSV contains **deliberately seeded edge cases**: duplicates, an outlier, an ambiguous merchant, and one malformed row. Your agent should handle these gracefully — see the brief for the required failure-mode behaviour.
- All amounts are in EUR. Expenses are negative; income is positive.
- The "expected anomalies" reference we use for grading is **not** included in this pack. Design your own evaluation harness based on what you observe in the data.

Good luck — we look forward to seeing what you build.
