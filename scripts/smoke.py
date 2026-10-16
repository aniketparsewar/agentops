"""Smoke test: health -> ask_agent -> metrics. Run with the server up."""
import json
import os
import sys

import httpx

BASE = os.environ.get("AGENTOPS_URL", "http://127.0.0.1:8000")
KEY = os.environ.get("API_KEY") or (sys.argv[1] if len(sys.argv) > 1 else "")
assert KEY, "set API_KEY env var or pass it as argv[1]"
H = {"X-API-Key": KEY}

r = httpx.get(f"{BASE}/health", timeout=30)
print("health:", r.status_code, r.text[:120])
r.raise_for_status()

r = httpx.post(
    f"{BASE}/ask_agent",
    headers={**H, "Content-Type": "application/json"},
    json={"question": "What is my new balance?"},
    timeout=120,
)
print("ask_agent:", r.status_code)
body = r.json()
print("answer:", body["answer"][:200])
print("watcher:", json.dumps(body["watcher"]))
print("cost_usd:", body["cost_usd"], "latency_ms:", body["latency_ms"])

r = httpx.get(f"{BASE}/metrics", headers=H, timeout=30)
m = r.json()
print("metrics: requests_total =", m["requests_total"],
      "| watcher =", json.dumps(m["watcher"]))
