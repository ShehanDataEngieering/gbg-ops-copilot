"""Chat models by role. Every model goes through Command Code with one key.

COPILOT_PROFILE=dev (default) uses the free Ling model; =release uses Claude.
The eval judge is GPT-6 Sol in both, so it never grades its own work.
"""

from __future__ import annotations

import os

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

_BASE = "https://api.commandcode.ai/provider"

_MODELS = {
    "dev": {"main": "inclusionai/ling-3.0-flash-sante:free", "triage": "inclusionai/ling-3.0-flash-sante:free"},
    "release": {"main": "claude-sonnet-5-5", "triage": "claude-haiku-4-5-20251001"},
}
_JUDGE = "gpt-6-sol"


def chat_model(role: str, *, profile: str | None = None):
    """role is "main", "triage" or "judge"."""
    key = os.environ["COMMANDCODE_API_KEY"]
    name = _JUDGE if role == "judge" else _MODELS[profile or os.getenv("COPILOT_PROFILE", "dev")][role]
    if name.startswith("claude-"):
        # The Anthropic SDK appends /v1/messages itself.
        return ChatAnthropic(model=name, base_url=_BASE, api_key=key)
    return ChatOpenAI(model=name, base_url=f"{_BASE}/v1", api_key=key)
