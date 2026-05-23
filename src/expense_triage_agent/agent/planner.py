"""Planner: explicitly decompose requests into sub-tasks.

The planner breaks down the user's instruction into concrete steps
and decides which tools to invoke in which order.
"""

from typing import TypedDict


class Plan(TypedDict, total=False):
    """Explicit plan for processing transactions."""
    steps: list[str]  # ordered list of tool calls: "categorize", "detect_anomalies", "summarize", "human_review"
    use_llm: bool  # whether to use Ollama for low-confidence cases
    review_threshold: float  # confidence threshold for flagging items for human review


def plan(instruction: str) -> Plan:
    """Decompose user instruction into ordered sub-tasks.
    
    Args:
        instruction: Natural language instruction from user
    
    Returns:
        Plan dict with explicit steps and parameters
    """
    instruction_lower = instruction.lower()
    
    # Start with default steps
    steps = ["categorize", "detect_anomalies", "summarize"]
    use_llm = True  # Default: use LLM for ambiguous cases
    review_threshold = 0.75  # Default: flag items with <75% confidence
    
    # Decide: should we use LLM?
    if "fast" in instruction_lower or "quick" in instruction_lower or "no ai" in instruction_lower or "offline" in instruction_lower:
        use_llm = False
    
    # Decide: should we include human review checkpoint?
    if "review" in instruction_lower or "confirm" in instruction_lower or "human" in instruction_lower:
        steps.insert(len(steps) - 1, "human_review")
    
    # Decide: different review thresholds
    if "strict" in instruction_lower or "careful" in instruction_lower:
        review_threshold = 0.85  # Stricter: flag more items
    elif "lenient" in instruction_lower or "permissive" in instruction_lower:
        review_threshold = 0.60  # More lenient: fewer false positives
    
    return {
        "steps": steps,
        "use_llm": use_llm,
        "review_threshold": review_threshold,
    }