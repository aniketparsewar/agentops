# AgentOps — project brief

**Thesis:** Project 6 Day 2 proved operational metrics can't see
correctness — a wrong answer looked like a healthy request. AgentOps
closes that gap: the eval harness watches the live agent and `/metrics`
reports the correctness pass rate next to latency and cost.

## Provenance (nothing is new except the wiring)

| Piece | From | Adapted how |
|-------|------|-------------|
| Agent loop | Project 4 `src/loop.py` | same plan/act split; `ask_statement` became an HTTP call |
| `calculator`, `read_file`, `write_file` | Project 4 `src/tools.py` | unchanged semantics |
| Service shell (auth, guardrails, observability, Dockerfile, render.yaml) | Project 6 | budget guardrail kept; `replay()` kept |
| Eval checks (keyword + citation) | Projects 2/3 | now run live per-answer, not in a batch script |
| ShipDocChat | Project 6 (deployed) | consumed as a tool over HTTP, not vendored |

## Day plan (Aniket controls the pace — no next day until he says so)

- **Day 1 — scaffold runs.** `pip install -r requirements.txt`, `.env`,
  `uvicorn app.main:app --reload`, `python scripts/smoke.py`. Ask via the
  UI; watch the tool calls in the response. Quiz before closing.
- **Day 2 — the watcher.** Add golden cases; break the agent on purpose
  (bad golden answer, adversarial question) and watch the pass rate drop
  in `/metrics`. The metric that was missing now moves. Quiz.
- **Day 3 — adversarial agent testing.** Project 4's boundary lessons,
  applied to the service: destructive tool calls, prompt-injecting the
  *agent* (not just the RAG), budget exhaustion mid-task. Quiz.
- **Day 4 — deploy.** Render Blueprint, public URL, one real user, watch
  the watcher score a stranger. README "What I learned". Closing quiz.

## Open questions for later days

- Should the watcher sample (every Nth answer) instead of scoring all?
  (Cost/latency tradeoff.)
- Paraphrase matching for golden cases — when does keyword checking stop
  being enough?
- The agent's ShipDocChat spend counts against the *agent's* budget.
  Is that the right accounting, or should tool spend have its own budget?
