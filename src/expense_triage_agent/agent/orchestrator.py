from typing import Dict, Any
from .planner import plan
from ..tools.categorize import categorize
from ..tools.anomalies import detect_anomalies
from ..tools.summarize import summarize
from ..domain.models import Transaction, CategorizedTransaction
from ..config.settings import settings


class Orchestrator:
    """Orchestrates the expense triage workflow.
    
    Flow:
    1. Planner decomposes the instruction into explicit steps
    2. Categorize transactions (rules + optional LLM for ambiguous)
    3. Detect anomalies (duplicates, outliers, ambiguous merchants)
    4. Summarize (totals + optional LLM-generated narrative)
    5. Optional: pause for human review if low-confidence items exist
    """
    
    def __init__(self, settings_obj=None):
        self.settings = settings_obj or settings

    def run(self, instruction: str, transactions: list[dict]) -> Dict[str, Any]:
        """Run the triage workflow.
        
        Args:
            instruction: User instruction (e.g., "categorize and flag anomalies")
            transactions: List of transaction dicts from CSV
        
        Returns:
            State dict with ledger, anomalies, summary, and optional review_candidates
        """
        # Step 1: Planner decomposes the instruction
        plan_result = plan(instruction)
        steps = plan_result["steps"]
        use_llm = plan_result["use_llm"]
        review_threshold = plan_result["review_threshold"]
        
        state: Dict[str, Any] = {
            "instruction": instruction,
            "transactions": transactions,
            "plan": plan_result,
        }

        # Step 2: Categorize transactions
        if "categorize" in steps:
            ledger: list[CategorizedTransaction] = []
            for raw in transactions:
                try:
                    tx = Transaction.model_validate(raw)
                except Exception:
                    continue
                category, confidence = categorize(tx, use_llm=use_llm)
                ledger.append(
                    CategorizedTransaction(**tx.model_dump(), category=category, confidence=confidence)
                )
            state["ledger"] = ledger
            # Flag items below review threshold
            state["review_needed"] = any(item.confidence < review_threshold for item in ledger)

        # Step 3: Detect anomalies
        if "detect_anomalies" in steps:
            anomalies = detect_anomalies(state.get("ledger", []))
            state["anomalies"] = anomalies

        # Step 4: Summarize
        if "summarize" in steps:
            summary = summarize(state.get("ledger", []), state.get("anomalies", []), use_llm=use_llm)
            state["summary"] = summary

        # Step 5: Human review (optional)
        if "human_review" in steps and state.get("review_needed"):
            # Collect low-confidence items for user review
            review = [
                {
                    "transaction_id": tx.transaction_id,
                    "merchant": tx.merchant,
                    "amount": tx.amount,
                    "category": tx.category,
                    "confidence": tx.confidence,
                }
                for tx in state.get("ledger", [])
                if tx.confidence < review_threshold
            ]
            state["review_candidates"] = review

        return state

    def apply_corrections_and_finalize(self, ledger: list[dict], corrections: Dict[str, str]) -> Dict[str, Any]:
        """Apply user corrections and finalize the ledger.
        
        Args:
            ledger: Original parsed transaction dicts
            corrections: Dict mapping transaction_id -> corrected_category
        
        Returns:
            Final ledger, anomalies, and summary
        """
        categorized = []
        for raw in ledger:
            try:
                tx = Transaction.model_validate(raw)
            except Exception:
                continue
            category = corrections.get(tx.transaction_id)
            if category:
                # User-corrected: high confidence
                categorized.append(
                    CategorizedTransaction(**tx.model_dump(), category=category, confidence=1.0)
                )
            else:
                # Keep original categorization
                cat, conf = categorize(tx, use_llm=False)  # No LLM for finalization
                categorized.append(
                    CategorizedTransaction(**tx.model_dump(), category=cat, confidence=conf)
                )

        anomalies = detect_anomalies(categorized)
        summary = summarize(categorized, anomalies, use_llm=False)
        return {"ledger": categorized, "anomalies": anomalies, "summary": summary}
