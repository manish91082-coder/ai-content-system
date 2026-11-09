"""Credential and model-catalogue smoke test.

This performs metadata-only GET/list calls. It does not submit prompts, consume
inference tokens, create content, or publish to social platforms.
"""
import os
import sys

GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or "gemini-3.5-flash-lite").strip()
GROQ_MODEL = (os.getenv("GROQ_MODEL") or "openai/gpt-oss-120b").strip()


def safe_error(error, secret):
    message = str(error)
    if secret:
        message = message.replace(secret, "[REDACTED]")
    return message[:350]


def check_gemini():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("Gemini: SKIPPED (GEMINI_API_KEY secret not configured)")
        return None
    try:
        from google import genai
        client = genai.Client(api_key=key)
        names = [str(item.name).replace("models/", "") for item in client.models.list()]
        if GEMINI_MODEL not in names:
            print(f"Gemini: AUTHENTICATED, MODEL_NOT_LISTED ({GEMINI_MODEL})")
            return False
        print(f"Gemini: AUTHENTICATED, MODEL_LISTED ({GEMINI_MODEL})")
        return True
    except Exception as error:
        print(f"Gemini: FAILED ({type(error).__name__}): {safe_error(error, key)}")
        return False


def check_groq():
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        print("Groq: SKIPPED (GROQ_API_KEY secret not configured)")
        return None
    try:
        from groq import Groq
        client = Groq(api_key=key)
        models = client.models.list()
        ids = [str(item.id) for item in models.data]
        if GROQ_MODEL not in ids:
            print(f"Groq: AUTHENTICATED, MODEL_NOT_LISTED ({GROQ_MODEL})")
            return False
        print(f"Groq: AUTHENTICATED, MODEL_LISTED ({GROQ_MODEL})")
        return True
    except Exception as error:
        print(f"Groq: FAILED ({type(error).__name__}): {safe_error(error, key)}")
        return False


def main():
    results = [check_gemini(), check_groq()]
    configured = [result for result in results if result is not None]
    healthy = [result for result in configured if result is True]
    if not configured:
        print("Provider check: SKIPPED (no provider secrets configured)")
        return 0
    if not healthy:
        print("Provider check: FAILED (no configured provider is healthy)")
        return 1
    if len(healthy) != len(configured):
        print("Provider check: DEGRADED (at least one provider is healthy; inspect failed-provider diagnostics)")
        return 0
    print("Provider check: PASS (all configured providers authenticated and target models listed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
