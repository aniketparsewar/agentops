"""Guardrails: rate limit, question length, daily cost budget. (From Project 6.)"""
import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException

RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "30"))
MAX_QUESTION_CHARS = 500
DAILY_BUDGET_USD = float(os.environ.get("DAILY_BUDGET_USD", "1.00"))

_hits: dict[str, deque] = defaultdict(deque)          # api_key -> timestamps
_spend: dict[str, list[tuple[float, float]]] = defaultdict(list)  # api_key -> [(ts, usd)]


def check_rate_limit(api_key: str) -> None:
    now = time.time()
    window = _hits[api_key]
    while window and window[0] <= now - 60:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Rate limit exceeded (30/min).")
    window.append(now)


def check_question(question: str) -> str:
    q = (question or "").strip()
    if not q:
        raise HTTPException(status_code=422, detail="Question is empty.")
    if len(q) > MAX_QUESTION_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"Question is {len(q)} chars (max {MAX_QUESTION_CHARS}).",
        )
    return q


def _prune_spend(api_key: str, now: float) -> float:
    entries = [(t, c) for t, c in _spend[api_key] if t > now - 86400]
    _spend[api_key] = entries
    return sum(c for _, c in entries)


def check_budget(api_key: str) -> None:
    """Reject if this key already spent its rolling-24h budget. Call before work."""
    if _prune_spend(api_key, time.time()) >= DAILY_BUDGET_USD:
        raise HTTPException(status_code=429, detail="Daily cost budget exceeded.")


def record_spend(api_key: str, cost_usd: float) -> None:
    """Record actual spend after the request completes."""
    now = time.time()
    _prune_spend(api_key, now)
    _spend[api_key].append((now, cost_usd))


def budget_remaining(api_key: str) -> float:
    return max(0.0, DAILY_BUDGET_USD - _prune_spend(api_key, time.time()))
