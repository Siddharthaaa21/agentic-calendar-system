import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    if LLM_PROVIDER == "anthropic":
        from anthropic import Anthropic
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)
    else:
        from groq import Groq
        _client = Groq(api_key=GROQ_API_KEY)

    return _client


def call_llm(prompt: str) -> str:
    client = _get_client()

    if LLM_PROVIDER == "anthropic":
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    chat = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return chat.choices[0].message.content


def call_llm_safe(prompt: str, fallback: str = ""):
    try:
        return call_llm(prompt)
    except Exception as e:
        logger.warning("LLM call failed; using fallback: %s", e)
        return fallback


if __name__ == "__main__":
    print(call_llm("What is the capital of India?"))
