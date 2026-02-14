# openrouter_client.py

"""
Drop-in OpenRouter integration for agent_router.py
Just add this file and update one import - no other code changes needed.
"""

import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# OpenRouter client (OpenAI-compatible)

_client = None


def get_openrouter_client():
    """Get or create OpenRouter client (singleton)"""
    global _client

    if _client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY environment variable not set. "
                "Get your key from https://openrouter.ai/keys"
            )

        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://your-site.com",  # Optional
                "X-Title": "SEO Agent"  # Shows in OpenRouter dashboard
            }
        )

        logger.info("OpenRouter client initialized")

    return _client


def run_agent(message: str, model: str = "openrouter/free") -> str:
    """
    Run agent with OpenRouter (auto-rotates through free models).

    Drop-in replacement for your existing run_agent() function.

    Args:
        message: User's message
        model: OpenRouter model (default: "openrouter/free" auto-rotates)

    Returns:
        Agent's response string
    """
    try:
        client = get_openrouter_client()

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"OpenRouter request failed: {e}")
        raise


# Alternative: Use specific free models instead of auto-rotation

OPENROUTER_FREE_MODELS = [
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-2-9b-it:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free"
]

_model_index = 0


def run_agent_rotate(message: str) -> str:
    """
    Manually rotate through specific free models (if you want control).
    """
    global _model_index

    model = OPENROUTER_FREE_MODELS[_model_index]
    _model_index = (_model_index + 1) % len(OPENROUTER_FREE_MODELS)

    return run_agent(message, model=model)
