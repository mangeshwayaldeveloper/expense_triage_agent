from collections import defaultdict
from ..domain.models import Anomaly, CategorizedTransaction, MonthlySummary
from ..llm.ollama_client import OllamaClient
import logging

logger = logging.getLogger(__name__)


def summarize(ledger: list[CategorizedTransaction], anomalies: list[Anomaly], use_llm: bool = True) -> MonthlySummary:
    """Generate monthly summary from ledger and anomalies.
    
    Uses LLM to generate a narrative if enabled, otherwise falls back to template.
    """
    totals = defaultdict(float)

    for row in ledger:
        if row.amount < 0:
            totals[row.category] += abs(row.amount)

    anomaly_count = len(anomalies)
    top_category = max(totals.items(), key=lambda item: item[1], default=("none", 0.0))[0]

    # Generate narrative with LLM if enabled
    if use_llm:
        narrative = _generate_narrative_with_llm(totals, anomalies, anomaly_count, top_category)
    else:
        narrative = (
            f"Most spend went to {top_category}. "
            f"{anomaly_count} anomalies were flagged. "
            f"Review duplicates, outliers, and ambiguous merchants before finalizing."
        )

    return MonthlySummary(
        total_by_category=dict(totals),
        anomaly_count=anomaly_count,
        narrative=narrative,
    )


def _generate_narrative_with_llm(totals: dict, anomalies: list[Anomaly], anomaly_count: int, top_category: str) -> str:
    """Use Ollama to generate a narrative summary.
    
    Handles timeouts and errors gracefully.
    """
    try:
        client = OllamaClient()
        
        # Build context for LLM
        category_text = "; ".join([f"{k}: €{v:.2f}" for k, v in sorted(totals.items(), key=lambda x: x[1], reverse=True)])
        anomaly_text = "; ".join([f"{a.merchant} ({a.reason})" for a in anomalies[:5]]) if anomalies else "None"
        
        prompt = f"""You are a financial advisor. Summarize this month's spending:
Top categories: {category_text}
Anomalies flagged: {anomaly_text}
Total anomalies: {anomaly_count}

Write a 1-2 sentence summary suitable for a financial report. Be concise and actionable."""
        
        response = client.generate(prompt, temperature=0.7)
        if response and response.strip():
            return response.strip()
        else:
            logger.warning("LLM returned empty narrative")
            return f"Most spending in {top_category}. {anomaly_count} anomalies flagged."
    except Exception as e:
        logger.error(f"LLM error in narrative generation: {e}")
        # Graceful fallback
        return f"Most spending in {top_category}. {anomaly_count} anomalies flagged."