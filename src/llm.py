"""LLM client helpers.

Two things live here:

1. ``chat_complete`` - a thin wrapper over any OpenAI-compatible endpoint,
   used by the answering agent (the system under test).
2. ``CustomJudge`` - a ``DeepEvalBaseLLM`` implementation so DeepEval's
   metrics can use the SAME OpenAI-compatible endpoint as the judge model.
   This lets you run the whole eval against OpenAI, Azure, a local vLLM/Ollama
   server, or any OpenAI-compatible gateway.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Optional, Type

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "not-needed"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )


def agent_model() -> str:
    return os.getenv("AGENT_MODEL", "gpt-4o-mini")


def judge_model() -> str:
    return os.getenv("JUDGE_MODEL", "gpt-4o")


def chat_complete(prompt: str, model: Optional[str] = None, temperature: float = 0.0) -> str:
    resp = get_client().chat.completions.create(
        model=model or agent_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


# --------------------------------------------------------------------------- #
# DeepEval custom judge (works with any OpenAI-compatible endpoint)
# --------------------------------------------------------------------------- #
try:
    from deepeval.models import DeepEvalBaseLLM

    class CustomJudge(DeepEvalBaseLLM):
        """Route DeepEval metric judging through an OpenAI-compatible endpoint."""

        def __init__(self, model: Optional[str] = None):
            self.model = model or judge_model()
            self.client = get_client()

        def load_model(self):
            return self.client

        def _call(self, prompt: str, schema: Optional[Type] = None):
            if schema is None:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                )
                return resp.choices[0].message.content or ""
            # Structured output: ask for JSON and parse into the pydantic schema.
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Respond ONLY with a valid JSON object that "
                        "matches the requested schema. No prose, no markdown.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            return schema(**json.loads(content))

        def generate(self, prompt: str, schema: Optional[Type] = None):
            return self._call(prompt, schema)

        async def a_generate(self, prompt: str, schema: Optional[Type] = None):
            return self._call(prompt, schema)

        def get_model_name(self) -> str:
            return f"custom:{self.model}"

except ImportError:  # deepeval not installed yet
    CustomJudge = None  # type: ignore
