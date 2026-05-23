from fastapi import APIRouter, UploadFile, File, HTTPException
from ..agent.orchestrator import Orchestrator
from ..services.transaction_loader import load_transactions_from_bytes
from typing import Dict
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()
orch = Orchestrator()


def _to_plain(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    return value


def _sse(event: str, data: Dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/triage")
async def triage(file: UploadFile = File(...), instruction: str = "categorize everything and flag anything unusual this month"):
    content = await file.read()
    rows, errors = load_transactions_from_bytes(content)
    state = orch.run(instruction, rows)
    # include parsing errors so caller can see skipped rows
    state["parse_errors"] = errors
    # expose review candidates if low-confidence
    if state.get("review_needed"):
        # collect low-confidence items
        review = [
            {
                "transaction_id": tx.transaction_id,
                "merchant": tx.merchant,
                "amount": tx.amount,
                "category": tx.category,
                "confidence": tx.confidence,
            }
            for tx in state.get("ledger", [])
            if tx.confidence < orch.settings.TEMPERATURE
        ]
        state["review_candidates"] = review
    return state


@router.post("/triage/confirm")
async def triage_confirm(payload: Dict):
    # payload: { "ledger": [...raw rows...], "corrections": { transaction_id: category } }
    ledger = payload.get("ledger")
    corrections = payload.get("corrections")
    if ledger is None or corrections is None:
        raise HTTPException(status_code=400, detail="ledger and corrections required")
    result = orch.apply_corrections_and_finalize(ledger, corrections)
    return result


@router.post("/triage/confirm/stream")
async def triage_confirm_stream(payload: Dict):
    """Stream confirm progress and final result using text/event-stream."""
    ledger = payload.get("ledger")
    corrections = payload.get("corrections")
    if ledger is None or corrections is None:
        raise HTTPException(status_code=400, detail="ledger and corrections required")

    async def event_stream():
        yield _sse("status", {"step": "received", "message": "Confirm request received"})
        await asyncio.sleep(0)
        yield _sse("status", {"step": "finalize", "message": "Applying corrections and recomputing summary"})
        result = orch.apply_corrections_and_finalize(ledger, corrections)
        plain_result = _to_plain(result)
        yield _sse("result", plain_result)
        yield _sse("done", {"ok": True})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )