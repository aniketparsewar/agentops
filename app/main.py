"""AgentOps: a self-evaluating agent service.

POST /ask_agent -> the agent loop (Project 4) plans, Python acts. Tools:
the deployed ShipDocChat service over HTTP (Project 6 as a tool),
calculator, sandboxed file tools. Every answer is scored by the eval
watcher (Projects 2/3) against evals/golden.json, and /metrics reports
the correctness pass rate next to latency and cost.
"""
import time
from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="AgentOps")

load_dotenv()  # before auth reads env vars at import

from . import agent, auth, guardrails, observability, watcher

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@app.on_event("startup")
def _startup() -> None:
    observability.replay()
    print(f"AgentOps up. Watcher golden cases: {watcher.golden_count()}")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "watcher_cases": watcher.golden_count()}


@app.post("/ask_agent")
async def ask_agent(req: AskRequest, api_key: str = Depends(auth.require_key)) -> dict:
    t0 = time.perf_counter()
    guardrails.check_rate_limit(api_key)
    guardrails.check_budget(api_key)
    question = guardrails.check_question(req.question)
    try:
        result = agent.run(question)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    guardrails.record_spend(api_key, result["cost_usd"])

    verdict = watcher.score(question, result["answer"], result.get("citations", []))
    remaining = guardrails.budget_remaining(api_key)
    observability.log_event({
        "endpoint": "ask_agent",
        "latency_ms": result["latency_ms"],
        "question": question,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "cost_usd": result["cost_usd"],
        "tool_calls": len(result["tool_calls"]),
        "watcher_evaluated": verdict["evaluated"],
        "watcher_passed": verdict["passed"] or False,
        "budget_remaining": remaining,
    })
    return {
        "answer": result["answer"],
        "tool_calls": result["tool_calls"],
        "citations": result["citations"],
        "latency_ms": result["latency_ms"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "cost_usd": result["cost_usd"],
        "watcher": verdict,
        "budget_remaining": remaining,
        "note": f"served in {round(time.perf_counter() - t0, 1)}s wall time",
    }


@app.get("/metrics")
def metrics(api_key: str = Depends(auth.require_key)) -> dict:
    guardrails.check_rate_limit(api_key)
    m = observability.get_metrics()
    m["watcher"]["golden_cases"] = watcher.golden_count()
    return m


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
