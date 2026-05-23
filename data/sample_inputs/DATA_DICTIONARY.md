# Data Dictionary — `transactions.csv`

One month of transactions (October 2025) from a small personal/household setup. All amounts are in EUR. Expenses are negative; the single income row is positive.

| Column | Type | Notes |
|---|---|---|
| `transaction_id` | string | Unique identifier in the form `TX1234`. Stable across the file. |
| `date` | ISO date (`YYYY-MM-DD`) | Transaction posting date. May not match the actual purchase date. |
| `merchant` | string | Raw merchant string as it appears on the bank statement. May be abbreviated, contain store numbers, or use payment-processor prefixes (e.g. `LYF*…`). |
| `description` | string | Optional free-text description. May be empty. |
| `amount` | decimal as string | Signed amount. Negative = money out, positive = money in. |
| `currency` | string | ISO 4217 currency code. All rows here are `EUR`. |
| `account` | string | IBAN of the account the transaction posted to. Two accounts are present in this dataset. |

## Things to be aware of

- The file contains at least one **malformed row** — your agent should skip it gracefully and report it, not crash.
- Merchant strings are **not pre-categorized**. The same merchant may appear with slightly different formatting across rows.
- Some merchants use **payment-processor prefixes** (e.g. `LYF*38291`) that are genuinely ambiguous about what was purchased.
- One row contains an **unusually large amount** for its likely category.
- The file contains at least one apparent **duplicate charge** (same merchant, same date, same amount).
- Several rows have **no description**; the merchant string is your only signal.
