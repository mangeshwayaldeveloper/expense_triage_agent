from fastapi import FastAPI
from .api.routes import router as api_router

app=FastAPI(title="Expense Triage Agent", version="0.1.0")

app.include_router(api_router,prefix="/v1")

@app.get("/health")
def health()-> dict[str,str]:
    return {"status":"ok"}
