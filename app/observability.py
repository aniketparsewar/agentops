"""Observability: JSONL request log (durable) + in-memory aggregates (fast)
+ replay at startup so /metrics survives restarts. (From Project 6.)

Adds watcher stats: the eval watcher scores answers against the golden
set, and /metrics reports the correctness pass rate next to latency —
the metric Project 6 Day 2 proved was missing.
"""
import json
import statistics
import threading
import time
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "requests.jsonl"
MAX_KEPT_LATENCIES = 10_000

_lock = threading.Lock()
_events: list[dict] = []
_latencies: dict[str, list[float]] = {}
_watcher_evaluated = 0
_watcher_passed = 0


def log_event(event: dict) -> None:
    global _watcher_evaluated, _watcher_passed
    event = dict(event)
    event.setdefault("ts", time.time())
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        _events.append(event)
        lat = _latencies.setdefault(event["endpoint"], [])
        lat.append(event["latency_ms"])
        if len(lat) > MAX_KEPT_LATENCIES:
            del lat[: len(lat) - MAX_KEPT_LATENCIES]
        if event.get("watcher_evaluated"):
            _watcher_evaluated += 1
            if event.get("watcher_passed"):
                _watcher_passed += 1


def replay() -> None:
    """Rebuild in-memory aggregates from the JSONL log at startup."""
    global _watcher_evaluated, _watcher_passed
    if not LOG_FILE.exists():
        return
    with _lock:
        for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue  # a corrupt log line must never kill startup
            _events.append(event)
            _latencies.setdefault(event["endpoint"], []).append(event["latency_ms"])
            if event.get("watcher_evaluated"):
                _watcher_evaluated += 1
                if event.get("watcher_passed"):
                    _watcher_passed += 1


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = min(int(p / 100 * len(ordered)), len(ordered) - 1)
    return round(ordered[k], 1)


def get_metrics() -> dict:
    with _lock:
        lat = _latencies.get("ask_agent", [])
        total_cost = round(sum(e.get("cost_usd", 0.0) for e in _events), 6)
        in_tok = sum(e.get("input_tokens", 0) for e in _events)
        out_tok = sum(e.get("output_tokens", 0) for e in _events)
        by_endpoint: dict[str, int] = {}
        for e in _events:
            by_endpoint[e["endpoint"]] = by_endpoint.get(e["endpoint"], 0) + 1
        evaluated, passed = _watcher_evaluated, _watcher_passed
    return {
        "requests_total": len(_events),
        "requests_by_endpoint": by_endpoint,
        "ask_agent_latency_ms": {
            "count": len(lat),
            "avg": round(statistics.fmean(lat), 1) if lat else 0.0,
            "p50": _pct(lat, 50),
            "p95": _pct(lat, 95),
        },
        "tokens": {"input": in_tok, "output": out_tok},
        "cost_usd_total": total_cost,
        "watcher": {
            "golden_cases": None,  # filled by main.py (needs watcher import)
            "evaluated": evaluated,
            "passed": passed,
            "pass_rate": round(passed / evaluated, 3) if evaluated else 0.0,
        },
    }
