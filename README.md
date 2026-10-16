# AgentOps — a self-evaluating agent service

The capstone: everything from the last six projects, wired together.

- **Agent loop** (Project 4): the model plans, Python acts. Tools are
  `shipdocchat_ask`, `calculator`, `read_file`, `write_file`.
- **Project 6 as a tool**: `shipdocchat_ask` calls the *deployed*
  ShipDocChat service (https://ship-docchat.onrender.com) over HTTP.
  Your RAG service is now someone else's tool.
- **Eval watcher** (Projects 2/3): every agent answer is scored against
  `evals/golden.json` (keyword + citation checks). `/metrics` reports
  the correctness **pass rate** next to latency and cost — the metric
  Project 6 Day 2 proved was missing from every dashboard.
- **Service shell** (Project 6): X-API-Key auth, rate limit, question
  length cap, $1/day cost budget per key, JSONL log + `replay()` so
  `/metrics` survives restarts, Dockerfile + Render Blueprint.

> **Demo data honesty note:** the golden answers cite the *fictional*
> Nebula Bank sample statement. Made-up fixture, not real financial data.

## Quickstart (local)

```bash
pip install -r requirements.txt
cp .env.example .env   # OPENAI_API_KEY, API_KEY, SHIPDOCCHAT_API_KEY
uvicorn app.main:app --reload
# open http://127.0.0.1:8000
python scripts/smoke.py <API_KEY>
```

## Endpoints

| Method | Path         | Auth | What it does |
|--------|--------------|------|--------------|
| GET    | `/health`    | no   | liveness + watcher case count |
| POST   | `/ask_agent` | key  | agent answer + tool calls + watcher verdict |
| GET    | `/metrics`   | key  | requests, p50/p95, tokens, cost, **watcher pass rate** |
| GET    | `/`          | no   | minimal web UI |

## Environment variables

| Var | Required | What |
|-----|----------|------|
| `OPENAI_API_KEY` | yes | agent's own LLM calls |
| `API_KEY` | yes | this service's client key |
| `SHIPDOCCHAT_URL` | yes | deployed ShipDocChat base URL |
| `SHIPDOCCHAT_API_KEY` | yes | key for the ShipDocChat service |
| `DAILY_BUDGET_USD` | no | per-key rolling 24h budget (default 1.00) |
| `RATE_LIMIT_PER_MIN` | no | per-key req/min (default 30) |

Note: the agent's spend includes the ShipDocChat tool's reported
`cost_usd` — the budget guardrail sees the *total* cost of an answer,
not just this service's LLM calls.

## Deploy

Render Blueprint via `render.yaml` (same pattern as Project 6).
Set `OPENAI_API_KEY` and `SHIPDOCCHAT_API_KEY` as secrets in the
dashboard; `API_KEY` auto-generates.

## Known demo-grade limits

- Single shared API key; no per-user keys or OAuth.
- Rate limiter and budget are per-process memory (production: Redis).
- Watcher matches golden cases by normalized question text — paraphrases
  aren't evaluated (production: semantic matching or an LLM judge).
- Keyword checks are brittle by design; they catch regressions, not
  prove correctness.

## What I learned

- *(fill in after the project closes)*
