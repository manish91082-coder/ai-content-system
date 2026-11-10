#!/usr/bin/env python3
"""Strict zero-spend OpenRouter gateway. Never falls back to a paid model."""
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("OPENROUTER_FREE_MODEL", "openrouter/free")
BASE = "https://openrouter.ai/api/v1/chat/completions"

class FreeModelUnavailable(RuntimeError):
    pass

def generate(system_prompt, user_prompt, max_tokens=2500):
    if not API_KEY:
        raise FreeModelUnavailable("OPENROUTER_API_KEY is not configured")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max(1, min(int(max_tokens), 4000)),
        "temperature": 0.2
    }
    request = Request(
        BASE,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + API_KEY,
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/manish91082-coder/ai-content-system",
            "X-Title": "Nexus Cloud Work Engine"
        },
        method="POST"
    )
    try:
        with urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (402, 429):
            raise FreeModelUnavailable("Free model capacity unavailable; paid fallback is disabled") from None
        raise RuntimeError("Model provider HTTP " + str(exc.code)) from None
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Model request failed: " + type(exc).__name__) from None
    choices = result.get("choices") or []
    if not choices:
        raise RuntimeError("Model returned no completion")
    content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Model returned empty content")
    return {"model": result.get("model"), "content": content, "usage": result.get("usage")}

def main():
    print(json.dumps({
        "status": "ready" if API_KEY else "needs_openrouter_api_key",
        "model": MODEL,
        "spend_policy": "free-model-route-only; no paid fallback",
        "key_present": bool(API_KEY)
    }))

if __name__ == "__main__":
    main()
