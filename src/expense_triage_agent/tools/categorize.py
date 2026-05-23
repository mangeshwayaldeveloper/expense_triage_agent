from ..domain.models import Transaction
from ..llm.ollama_client import OllamaClient
import logging

logger = logging.getLogger(__name__)

RULES = {
    "uber": "transport",
    "bolt": "transport",
    "lidl": "groceries",
    "aldi": "groceries",
    "albert heijn": "groceries",
    "jumbo": "groceries",
    "marqt": "groceries",
    "ikea": "household",
    "water": "utilities",
    "electric": "utilities",
    "vattenfall": "utilities",
    "kpn": "utilities",
    "t-mobile": "utilities",
    "netflix": "subscriptions",
    "spotify": "subscriptions",
    "hema": "household",
    "kruidvat": "household",
    "etos": "household",
    "shell": "fuel",
    "cafe": "dining",
    "pizza": "dining",
    "restaurant": "dining",
    "dominos": "dining",
    "pathe": "entertainment",
    "cinema": "entertainment",
    "mediamarkt": "electronics",
    "gucci": "fashion",
    "starbucks": "dining",
}

def categorize(transaction: Transaction, use_llm: bool = True) -> tuple[str, float]:
    """Categorize a transaction using rules first, then LLM for low-confidence cases.
    
    Args:
        transaction: Transaction to categorize
        use_llm: if True and rule confidence is low, consult Ollama
    
    Returns:
        (category, confidence) tuple
    """
    text = f"{transaction.merchant} {transaction.description or ''}".lower()

    # Try rule-based categorization first
    for keyword, category in RULES.items():
        if keyword in text:
            return category, 0.95

    # Ambiguous payment processor
    if transaction.merchant.startswith("LYF*"):
        # Use LLM for LYF* processors if enabled
        if use_llm:
            llm_cat, llm_conf = _categorize_with_llm(transaction)
            return llm_cat, llm_conf
        return "unknown", 0.45

    # Fallback: no rule matched
    if use_llm and not transaction.merchant.strip():
        # Empty merchant, skip LLM
        return "other", 0.30
    
    if use_llm:
        # Low-confidence fallback: ask LLM
        llm_cat, llm_conf = _categorize_with_llm(transaction)
        return llm_cat, llm_conf
    
    return "other", 0.60


def _categorize_with_llm(transaction: Transaction) -> tuple[str, float]:
    """Use Ollama to categorize ambiguous transactions.
    
    Handles timeouts and errors gracefully.
    """
    try:
        client = OllamaClient()
        prompt = f"""Categorize this transaction:
Merchant: {transaction.merchant}
Description: {transaction.description or 'N/A'}
Amount: {transaction.amount}

Choose ONE category from: groceries, transport, utilities, subscriptions, household, dining, entertainment, electronics, fashion, fuel, other
Reply with just the category word."""
        
        response = client.generate(prompt, temperature=0.3)
        if not response or not response.strip():
            logger.warning(f"LLM returned empty response for {transaction.transaction_id}")
            return "other", 0.50
        
        category = response.strip().lower().split()[0]
        # Validate category
        valid_categories = {
            "groceries", "transport", "utilities", "subscriptions", "household",
            "dining", "entertainment", "electronics", "fashion", "fuel", "other"
        }
        if category not in valid_categories:
            logger.warning(f"LLM returned invalid category '{category}' for {transaction.transaction_id}")
            return "other", 0.50
        
        return category, 0.75
    except Exception as e:
        logger.error(f"LLM error for {transaction.transaction_id}: {e}")
        # Graceful degradation: fall back to rule-based default
        return "other", 0.50