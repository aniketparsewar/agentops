"""The eval watcher: scores every agent answer against a golden set and
reports correctness as a metric. This is the capstone's thesis — Project 6
Day 2 taught that operational metrics can't see correctness, so the eval
harness (Projects 2/3) watches the live agent and /metrics reports the
pass rate next to latency and cost.
"""
import json
from pathlib import Path

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "evals" / "golden.json"


def _load() -> list[dict]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def _normalize(q: str) -> str:
    return " ".join(q.strip().lower().rstrip("?").split())


_INDEX = {_normalize(g["question"]): g for g in _load()}


def score(question: str, answer: str, citations: list) -> dict:
    """Score one agent answer against its golden case.

    Returns {"evaluated": bool, "passed": bool|None, "checks": [...]}.
    Questions with no golden case are not evaluated (not failures).
    """
    case = _INDEX.get(_normalize(question))
    if case is None:
        return {"evaluated": False, "passed": None, "checks": []}
    checks: list[dict] = []
    lowered = (answer or "").lower()
    for kw in case.get("must_contain", []):
        ok = kw.lower() in lowered
        checks.append({"check": f"answer contains '{kw}'", "passed": ok})
    if case.get("require_citation"):
        ok = bool(citations)
        checks.append({"check": "answer has citations", "passed": ok})
    passed = all(c["passed"] for c in checks) if checks else True
    return {"evaluated": True, "passed": passed, "checks": checks}


def golden_count() -> int:
    return len(_INDEX)
