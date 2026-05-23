import sys
import os

# Ensure `src` is on path when running via `streamlit run frontend/main.py`
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import streamlit as st
from expense_triage_agent.services.transaction_loader import load_transactions_from_bytes
from expense_triage_agent.agent.orchestrator import Orchestrator
import pandas as pd
from io import BytesIO
import requests
import json

st.set_page_config(page_title="Expense Triage Agent", layout="wide")
st.title("💰 Expense Triage Agent")

# Initialize orchestrator
orch = Orchestrator()

# Initialize session state
if "state" not in st.session_state:
    st.session_state.state = None
if "final_state" not in st.session_state:
    st.session_state.final_state = None
if "original_transactions" not in st.session_state:
    st.session_state.original_transactions = None
if "corrections" not in st.session_state:
    st.session_state.corrections = {}
if "confirm_payload" not in st.session_state:
    st.session_state.confirm_payload = None
if "confirm_response" not in st.session_state:
    st.session_state.confirm_response = None
if "stream_events" not in st.session_state:
    st.session_state.stream_events = []


def _as_dict(item):
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return item


def _append_stream_event(message: str):
    st.session_state.stream_events.append(message)
    # Keep only recent events to avoid runaway UI growth.
    if len(st.session_state.stream_events) > 100:
        st.session_state.stream_events = st.session_state.stream_events[-100:]

# Sidebar: Upload and configure
with st.sidebar:
    st.header("⚙️ Configuration")
    
    uploaded = st.file_uploader("📥 Upload transactions CSV", type=["csv"])
    
    if uploaded is not None:
        content = uploaded.read()
        rows, errors = load_transactions_from_bytes(content)
        
        st.subheader("Parse Status")
        if errors:
            st.warning(f"⚠️ {len(errors)} parse error(s):")
            for e in errors:
                st.caption(e)
        else:
            st.success(f"✓ {len(rows)} rows loaded successfully")
        
        st.session_state.original_transactions = rows
    
    instruction = st.text_area(
        "📝 Instruction",
        value="categorize everything and flag anything unusual this month",
        height=80
    )

    st.divider()
    st.subheader("Finalize Mode")
    finalize_mode = st.radio(
        "How to finalize corrections",
        options=[
            "Local orchestrator",
            "Backend API (/v1/triage/confirm)",
            "Backend API Stream (SSR/SSE)",
        ],
        index=1,
    )
    api_base_url = st.text_input("Backend URL", value="http://localhost:8000")

# Main workflow
if st.session_state.original_transactions is not None:
    rows = st.session_state.original_transactions
    
    # Step 1: Run triage
    if st.button("🚀 Run Triage", key="run_triage", use_container_width=True):
        with st.spinner("Running triage..."):
            state = orch.run(instruction, rows)
            st.session_state.state = state
            st.session_state.corrections = {}  # Reset corrections
            st.session_state.final_state = None
            st.session_state.stream_events = []
        st.success("✓ Triage complete!")
        st.rerun()

# Display triage results if available
if st.session_state.state is not None:
    state = st.session_state.state
    
    st.divider()
    st.header("📊 Triage Results")
    
    # Display metrics
    ledger = state.get("ledger", [])
    anomalies = state.get("anomalies", [])
    summary = state.get("summary")
    review_candidates = state.get("review_candidates", [])
    review_threshold = state.get("plan", {}).get("review_threshold", 0.75)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Transactions", len(ledger))
    with col2:
        st.metric("Anomalies Detected", len(anomalies))
    with col3:
        st.metric("Low-Confidence Items", len(review_candidates))
    with col4:
        st.metric("Review Threshold", f"{review_threshold:.0%}")
    
    st.divider()
    
    # Left column: Ledger and review
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        # Display full ledger
        st.subheader("📋 Ledger")
        df = pd.DataFrame([{
            "ID": tx.transaction_id,
            "Date": tx.date,
            "Merchant": tx.merchant,
            "Amount": f"{tx.amount:.2f}",
            "Category": tx.category,
            "Confidence": f"{tx.confidence:.0%}",
        } for tx in ledger])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Human review section (if needed)
        if review_candidates:
            st.divider()
            st.subheader("🔍 Human Review — Low-Confidence Items")
            st.info(
                f"Found {len(review_candidates)} item(s) with confidence below {review_threshold:.0%}. "
                "Please review and correct category assignments below."
            )
            
            # Create review form
            for idx, candidate in enumerate(review_candidates):
                with st.expander(
                    f"**{candidate['transaction_id']}** — {candidate['merchant']} ({candidate['amount']}) "
                    f"→ {candidate['category']} ({candidate['confidence']:.0%})",
                    expanded=(idx == 0)
                ):
                    cols = st.columns([3, 2])
                    with cols[0]:
                        st.write(f"**Merchant:** {candidate['merchant']}")
                        st.write(f"**Amount:** {candidate['amount']}")
                        st.write(f"**Current Category:** {candidate['category']}")
                        st.write(f"**Current Confidence:** {candidate['confidence']:.0%}")
                    
                    with cols[1]:
                        new_category = st.text_input(
                            "Corrected Category",
                            value=candidate["category"],
                            key=f"correction_{candidate['transaction_id']}",
                            placeholder="e.g., groceries, transport, dining"
                        )
                        if new_category != candidate["category"]:
                            st.session_state.corrections[candidate["transaction_id"]] = new_category
                        elif candidate["transaction_id"] in st.session_state.corrections:
                            del st.session_state.corrections[candidate["transaction_id"]]
            
            # Apply corrections button
            if st.session_state.corrections:
                st.success(f"✓ {len(st.session_state.corrections)} correction(s) ready to apply")
                if st.button("✅ Apply Corrections & Finalize", use_container_width=True):
                    with st.spinner("Applying corrections..."):
                        payload = {
                            "ledger": st.session_state.original_transactions,
                            "corrections": st.session_state.corrections,
                        }
                        st.session_state.confirm_payload = payload

                        if finalize_mode == "Backend API (/v1/triage/confirm)":
                            confirm_url = f"{api_base_url.rstrip('/')}/v1/triage/confirm"
                            try:
                                resp = requests.post(confirm_url, json=payload, timeout=20)
                                resp.raise_for_status()
                                result = resp.json()
                                st.session_state.final_state = result
                                st.session_state.confirm_response = result
                            except Exception as e:
                                st.error(
                                    f"Failed to call {confirm_url}. "
                                    f"Start backend with `uvicorn app:app --reload`. Details: {e}"
                                )
                                st.session_state.final_state = None
                                st.session_state.confirm_response = None
                                st.stop()
                        elif finalize_mode == "Backend API Stream (SSR/SSE)":
                            stream_url = f"{api_base_url.rstrip('/')}/v1/triage/confirm/stream"
                            status_box = st.empty()
                            events_box = st.empty()
                            try:
                                final_result = None
                                st.session_state.stream_events = []
                                with requests.post(stream_url, json=payload, stream=True, timeout=60) as resp:
                                    resp.raise_for_status()
                                    sse_state = {
                                        "event_name": None,
                                        "data_lines": [],
                                        "final_result": None,
                                    }

                                    def _flush_event():
                                        if sse_state["event_name"] is None:
                                            sse_state["data_lines"] = []
                                            return
                                        data_str = "\n".join(sse_state["data_lines"]).strip()
                                        data = {}
                                        if data_str:
                                            try:
                                                data = json.loads(data_str)
                                            except json.JSONDecodeError:
                                                data = {"raw": data_str}

                                        if sse_state["event_name"] == "status":
                                            msg = data.get("message", "Working...")
                                            _append_stream_event(f"STATUS: {msg}")
                                            status_box.info(f"Streaming update: {msg}")
                                        elif sse_state["event_name"] == "result":
                                            sse_state["final_result"] = data
                                            _append_stream_event("RESULT: Final payload received")
                                            status_box.success("Streaming update: Final result received")
                                        elif sse_state["event_name"] == "done":
                                            _append_stream_event("DONE: Stream finished")
                                            status_box.success("Streaming complete")
                                        else:
                                            _append_stream_event(f"EVENT {sse_state['event_name']}: {data}")

                                        events_box.code("\n".join(st.session_state.stream_events), language="text")
                                        sse_state["event_name"] = None
                                        sse_state["data_lines"] = []

                                    for raw_line in resp.iter_lines(decode_unicode=True):
                                        if raw_line is None:
                                            continue
                                        line = raw_line.strip()
                                        if line == "":
                                            _flush_event()
                                            continue
                                        if line.startswith("event:"):
                                            sse_state["event_name"] = line.split(":", 1)[1].strip()
                                            continue
                                        if line.startswith("data:"):
                                            sse_state["data_lines"].append(line.split(":", 1)[1].strip())

                                    _flush_event()

                                final_result = sse_state["final_result"]
                                if final_result is None:
                                    raise RuntimeError("Stream ended without a result event")

                                st.session_state.final_state = final_result
                                st.session_state.confirm_response = final_result
                            except Exception as e:
                                st.error(
                                    f"Failed to stream from {stream_url}. "
                                    f"Start backend with `uvicorn app:app --reload`. Details: {e}"
                                )
                                st.session_state.final_state = None
                                st.session_state.confirm_response = None
                                st.stop()
                        else:
                            result = orch.apply_corrections_and_finalize(
                                st.session_state.original_transactions,
                                st.session_state.corrections,
                            )
                            st.session_state.final_state = result
                            st.session_state.confirm_response = _as_dict(result)
                    st.success("✓ Corrections applied!")
                    st.rerun()
            else:
                st.info("No corrections made. Edit above to modify categories.")

            st.caption(
                "`/v1/triage/confirm` is used after human review to apply category corrections and return the finalized ledger, anomalies, and summary."
            )
    
    with col_right:
        st.subheader("🚨 Anomalies")
        if anomalies:
            for a in anomalies:
                severity_emoji = "🔴" if a.severity == "high" else "🟡"
                with st.expander(f"{severity_emoji} {a.transaction_id}"):
                    st.write(f"**Merchant:** {a.merchant}")
                    st.write(f"**Reason:** {a.reason}")
                    st.write(f"**Severity:** {a.severity.upper()}")
        else:
            st.info("No anomalies detected ✓")
        
        st.divider()
        st.subheader("📈 Summary")
        if summary:
            if summary.total_by_category:
                st.write("**Spending by Category:**")
                for cat, total in sorted(summary.total_by_category.items(), key=lambda x: x[1], reverse=True):
                    st.write(f"- {cat}: {total:.2f}")
            
            st.divider()
            if summary.narrative:
                st.write("**Narrative:**")
                st.write(summary.narrative)
            else:
                st.caption("(No narrative generated)")

# Display final state if corrections were applied
if st.session_state.final_state is not None:
    final = st.session_state.final_state
    final_ledger = final.get("ledger", [])
    final_anomalies = final.get("anomalies", [])
    final_summary = final.get("summary")
    final_summary_obj = _as_dict(final_summary) if final_summary else {}
    
    st.divider()
    st.header("✅ Finalized Ledger")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Final Transaction Count", len(final_ledger))
    with col2:
        st.metric("Final Anomalies", len(final_anomalies))
    with col3:
        if final_summary_obj and final_summary_obj.get("total_by_category"):
            total_spent = sum(final_summary_obj.get("total_by_category", {}).values())
            st.metric("Total Spent", f"{total_spent:.2f}")
    
    # Final ledger table
    df_final = pd.DataFrame([{
        "ID": _as_dict(tx).get("transaction_id"),
        "Date": _as_dict(tx).get("date"),
        "Merchant": _as_dict(tx).get("merchant"),
        "Amount": f"{float(_as_dict(tx).get('amount', 0.0)):.2f}",
        "Category": _as_dict(tx).get("category"),
        "Confidence": f"{float(_as_dict(tx).get('confidence', 0.0)):.0%}",
    } for tx in final_ledger])
    st.dataframe(df_final, use_container_width=True, hide_index=True)
    
    col_final_left, col_final_right = st.columns([2, 1])
    
    with col_final_left:
        # Download button for final ledger CSV
        csv_buffer = BytesIO()
        df_final.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue()
        
        st.download_button(
            label="📥 Download Final Ledger (CSV)",
            data=csv_bytes,
            file_name="final_ledger.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_final_right:
        # Download button for anomalies JSON
        anomalies_json = json.dumps([
            {
                "transaction_id": _as_dict(a).get("transaction_id"),
                "merchant": _as_dict(a).get("merchant"),
                "reason": _as_dict(a).get("reason"),
                "severity": _as_dict(a).get("severity"),
            }
            for a in final_anomalies
        ], indent=2)
        
        st.download_button(
            label="📥 Download Anomalies (JSON)",
            data=anomalies_json,
            file_name="anomalies.json",
            mime="application/json",
            use_container_width=True
        )
    
    st.divider()
    col_summary_left, col_summary_right = st.columns(2)
    
    with col_summary_left:
        st.subheader("Final Anomalies")
        if final_anomalies:
            for a in final_anomalies:
                ad = _as_dict(a)
                severity_emoji = "🔴" if ad.get("severity") == "high" else "🟡"
                st.write(
                    f"{severity_emoji} **{ad.get('transaction_id')}** "
                    f"({ad.get('merchant')}): {ad.get('reason')}"
                )
        else:
            st.success("No anomalies in final ledger ✓")
    
    with col_summary_right:
        st.subheader("Final Summary")
        if final_summary_obj:
            total_by_category = final_summary_obj.get("total_by_category", {})
            if total_by_category:
                st.write("**Spending by Category:**")
                for cat, total in sorted(total_by_category.items(), key=lambda x: x[1], reverse=True):
                    st.write(f"- {cat}: {total:.2f}")
            
            if final_summary_obj.get("narrative"):
                st.write("**Narrative:**")
                st.write(final_summary_obj.get("narrative"))

    st.divider()
    with st.expander("Show /v1/triage/confirm request & response", expanded=False):
        st.write("**Request payload sent to confirm endpoint:**")
        st.json(st.session_state.confirm_payload or {})
        st.write("**Response received from confirm endpoint:**")
        st.json(st.session_state.confirm_response or _as_dict(final))

    if st.session_state.stream_events:
        with st.expander("Show streamed events", expanded=False):
            st.code("\n".join(st.session_state.stream_events), language="text")
