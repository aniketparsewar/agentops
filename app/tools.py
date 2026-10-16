"""Agent tools. The model plans; Python acts. (Tool pattern from Project 4.)

- shipdocchat_ask: the DEPLOYED Project 6 service, called over HTTP as a tool.
- calculator: safe AST arithmetic.
- read_file / write_file: sandboxed to ./workspace_files/.
"""
import ast
import operator
import os
from pathlib import Path

import httpx

SHIPDOCCHAT_URL = os.environ.get("SHIPDOCCHAT_URL", "https://ship-docchat.onrender.com").rstrip("/")
SHIPDOCCHAT_API_KEY = os.environ.get("SHIPDOCCHAT_API_KEY", "")

WORKSPACE = Path(os.environ.get("AGENT_WORKSPACE", "./workspace_files"))
WORKSPACE.mkdir(parents=True, exist_ok=True)


# ---- shipdocchat_ask: Project 6 as a tool ----

def shipdocchat_ask(question: str, top_k: int = 3) -> dict:
    """Ask the deployed ShipDocChat RAG service. Returns its full JSON:
    answer, citations, chunk_scores, latency_ms, tokens, cost_usd, refused."""
    if not SHIPDOCCHAT_API_KEY:
        raise RuntimeError("SHIPDOCCHAT_API_KEY is not set.")
    top_k = max(1, min(int(top_k), 5))
    resp = httpx.post(
        f"{SHIPDOCCHAT_URL}/ask",
        headers={"X-API-Key": SHIPDOCCHAT_API_KEY, "Content-Type": "application/json"},
        json={"question": question, "top_k": top_k},
        timeout=60.0,
    )
    if resp.status_code == 429:
        raise RuntimeError(f"ShipDocChat rate-limited/budget-exceeded: {resp.text[:200]}")
    resp.raise_for_status()
    return resp.json()


# ---- calculator: safe AST math (from Project 4) ----

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
}


def calculator(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError("unsafe expression")

    return ev(tree)


# ---- read_file / write_file: sandboxed (from Project 4) ----

def _safe(name: str) -> Path:
    base = WORKSPACE.resolve()
    p = (base / name).resolve()
    if base != p and base not in p.parents:
        raise ValueError("path escapes workspace")
    return p


def read_file(name: str) -> str:
    return _safe(name).read_text(encoding="utf-8")


def write_file(name: str, content: str) -> str:
    p = _safe(name)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {name}"
