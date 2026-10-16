"""The agent loop: the model plans, Python acts. (Loop pattern from Project 4.)

Each turn the model outputs EITHER one tool-call JSON object OR a final
answer JSON object. Python executes the tool and feeds the result back.
The client is created lazily so importing this module without a key
never crashes.
"""
import json
import time

from openai import OpenAI

from . import costs, tools

MODEL = "gpt-4o-mini"
MAX_ITERS = 6

_client = None


_client_instance = None


def _client():
    global _client_instance
    if _client_instance is None:
        _client_instance = OpenAI()  # reads OPENAI_API_KEY from the environment
    return _client_instance



SYSTEM = """You are a document-analysis agent. You never act directly — you either call a tool or give the final answer.

TOOLS (exactly one per turn, as a JSON object):
{"tool": "shipdocchat_ask", "args": {"question": "<question for the statement chatbot>", "top_k": 3}}
  Ask the deployed statement chatbot about the credit card statement. Returns answer, citations, chunk_scores, cost_usd, refused.
{"tool": "calculator", "args": {"expression": "<python arithmetic, e.g. 3842.17 - 64.99>"}}
  Safe arithmetic only. Use it for any math instead of doing it yourself.
{"tool": "read_file", "args": {"name": "<filename in the workspace>"}}
  Read a workspace file.
{"tool": "write_file", "args": {"name": "<filename>", "content": "<full content>"}}
  Write a workspace file. Never overwrite, clear, or delete existing file contents without asking the user first.

RULES:
- Reason briefly, then output EITHER one tool-call object OR {"answer": "<final answer>"}.
- Output ONLY the JSON object — no prose around it.
- Every factual claim in the final answer must come from a tool result. Keep the statement chatbot's citations.
- If the tools don't contain the answer, say so plainly. Never invent numbers.
- Prefer the cheapest path: if one tool call answers the question, stop there.
"""


def _dispatch(name: str, args: dict):
    if name == "shipdocchat_ask":
        return tools.shipdocchat_ask(args["question"], int(args.get("top_k", 3)))
    if name == "calculator":
        return {"result": tools.calculator(args["expression"])}
    if name == "read_file":
        return {"content": tools.read_file(args["name"])}
    if name == "write_file":
        return {"ok": tools.write_file(args["name"], args["content"])}
    raise ValueError(f"unknown tool: {name}")


def run(question: str, max_iters: int = MAX_ITERS) -> dict:
    """Run the agent loop. Returns answer, tool_calls, citations, tokens,
    cost_usd (LLM + tool spend), latency_ms."""
    t0 = time.perf_counter()
    client = _client()
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    tool_calls: list[dict] = []
    citations: list[int] = []
    tool_cost = 0.0
    in_tokens = out_tokens = 0

    answer = "I couldn't complete the task within the step limit."
    for _ in range(max_iters):
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0
        )
        in_tokens += resp.usage.prompt_tokens
        out_tokens += resp.usage.completion_tokens
        raw = (resp.choices[0].message.content or "").strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"answer": raw}  # prose treated as final answer

        if "answer" in parsed:
            answer = parsed["answer"]
            break

        name = parsed.get("tool")
        args = parsed.get("args", {}) or {}
        tool_calls.append({"tool": name, "args": args})
        try:
            result = _dispatch(name, args)
            if name == "shipdocchat_ask" and isinstance(result, dict):
                tool_cost += float(result.get("cost_usd", 0.0) or 0.0)
                citations = [int(i) for i in result.get("citations", [])]
            observation = json.dumps(result)[:4000]
        except Exception as e:  # noqa: BLE001 — tool errors become observations
            observation = f"TOOL ERROR: {type(e).__name__}: {e}"
        messages.append({"role": "assistant", "content": raw})
        messages.append({
            "role": "user",
            "content": f"TOOL RESULT ({name}):\n{observation}\n\nContinue: next tool call or final answer as JSON.",
        })

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    llm_cost = costs.estimate(MODEL, in_tokens, out_tokens)
    return {
        "answer": answer,
        "tool_calls": tool_calls,
        "citations": citations,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "cost_usd": round(llm_cost + tool_cost, 6),
        "latency_ms": latency_ms,
    }
