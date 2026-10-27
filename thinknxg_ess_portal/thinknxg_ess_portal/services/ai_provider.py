"""Model provider adapters. Credentials stay on the server; responses normalised to:
{"text": str, "tool_calls": [{"id", "name", "input"}], "assistant_message": <provider-native message>}"""
import json
import frappe
import requests

TIMEOUT = 45


def _settings():
    s = frappe.get_cached_doc("ESS Portal Settings")
    return s, s.get_password("ai_api_key", raise_exception=False)


def enabled():
    s, key = _settings()
    return s.ai_provider in ("Anthropic", "OpenAI Compatible") and bool(key)


def provider_name():
    return frappe.get_cached_doc("ESS Portal Settings").ai_provider


def chat(system, messages, tools):
    s, key = _settings()
    if s.ai_provider == "Anthropic":
        return _anthropic(s, key, system, messages, tools)
    return _openai(s, key, system, messages, tools)


# ------------------------------------------------------------------ Anthropic Messages API
def _anthropic(s, key, system, messages, tools):
    payload = {"model": s.ai_model or "claude-sonnet-5-5", "max_tokens": 1200, "system": system,
               "messages": messages,
               "tools": [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
                         for t in tools]}
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=TIMEOUT, json=payload,
                      headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    r.raise_for_status()
    data = r.json()
    text, calls = "", []
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
        elif block.get("type") == "tool_use":
            calls.append({"id": block["id"], "name": block["name"], "input": block.get("input") or {}})
    return {"text": text, "tool_calls": calls, "assistant_message": {"role": "assistant", "content": data["content"]}}


def anthropic_tool_results(results):
    return {"role": "user", "content": [{"type": "tool_result", "tool_use_id": r["id"],
                                         "content": json.dumps(r["output"], default=str)} for r in results]}


# ------------------------------------------------------------------ OpenAI-compatible chat completions
def _openai(s, key, system, messages, tools):
    payload = {"model": s.ai_model, "messages": [{"role": "system", "content": system}] + messages,
               "tools": [{"type": "function", "function": t} for t in tools], "temperature": 0.2}
    r = requests.post(s.ai_base_url.rstrip("/") + "/chat/completions", timeout=TIMEOUT, json=payload,
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    calls = []
    for c in msg.get("tool_calls") or []:
        try:
            args = json.loads(c["function"].get("arguments") or "{}")
        except ValueError:
            args = {}
        calls.append({"id": c["id"], "name": c["function"]["name"], "input": args})
    return {"text": msg.get("content") or "", "tool_calls": calls, "assistant_message": msg}


def openai_tool_results(results):
    return [{"role": "tool", "tool_call_id": r["id"], "content": json.dumps(r["output"], default=str)}
            for r in results]


def tool_results_message(results):
    if provider_name() == "Anthropic":
        return [anthropic_tool_results(results)]
    return openai_tool_results(results)
