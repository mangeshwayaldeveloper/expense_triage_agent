from langgraph.graph import StateGraph, END
from .state import AgentState
from ..tools.categorize import categorize
from ..tools.anomalies import detect_anomalies
from ..tools.summarize import summarize
from ..domain.models import Transaction, CategorizedTransaction


def build_graph():
    graph = StateGraph(AgentState)

    def categorize_node(state: AgentState) -> AgentState:
        ledger: list[CategorizedTransaction] = []
        for raw in state.get("transactions", []):
            tx = Transaction.model_validate(raw)
            category, confidence = categorize(tx)
            ledger.append(
                CategorizedTransaction(
                    **tx.model_dump(),
                    category=category,
                    confidence=confidence,
                )
            )
        return {"ledger": ledger, "review_needed": any(item.confidence < 0.75 for item in ledger)}

    def anomaly_node(state: AgentState) -> AgentState:
        return {"anomalies": detect_anomalies(state.get("ledger", []))}

    def summary_node(state: AgentState) -> AgentState:
        return {"summary": summarize(state.get("ledger", []), state.get("anomalies", []))}

    graph.add_node("categorize", categorize_node)
    graph.add_node("detect_anomalies", anomaly_node)
    graph.add_node("summarize", summary_node)

    graph.set_entry_point("categorize")
    graph.add_edge("categorize", "detect_anomalies")
    graph.add_edge("detect_anomalies", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()