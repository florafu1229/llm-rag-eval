"""DeepEval test suite for the RAG agent.

Run with either:

    deepeval test run tests/test_rag_eval.py         # rich DeepEval report
    pytest tests/test_rag_eval.py -v                  # plain pytest

Each golden Q&A becomes one parametrized test case. For every case we score
four metrics:

  * AnswerRelevancy  - is the answer on-topic for the question?
  * Faithfulness     - is the answer grounded in the retrieved context? (anti-hallucination)
  * Hallucination    - does the answer contradict / invent facts vs the context?
  * Correctness (GEval) - does the answer match the expected/golden answer?
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from deepeval import assert_test
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    GEval,
    HallucinationMetric,
)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from src.agent import RagAgent
from src.llm import CustomJudge

_DATA = Path(__file__).resolve().parent.parent / "data" / "golden.json"
_GOLDEN = json.loads(_DATA.read_text(encoding="utf-8"))

# One agent instance shared across cases.
_AGENT = RagAgent()
_JUDGE = CustomJudge()

# Pass thresholds (0-1). Tune per your quality bar and judge strength.
# Small local judges (e.g. qwen2.5:3b) score erratically, so the default is
# lenient. Raise it (e.g. 0.8) when using a strong judge.
_THRESHOLD = float(os.getenv("EVAL_THRESHOLD", "0.5"))

# Local CPU judges are slow. By default we run a lean 2-metric set synchronously.
# Set FULL_METRICS=1 to also run Faithfulness + Hallucination (slower).
_FULL_METRICS = os.getenv("FULL_METRICS", "0") == "1"


def _metrics():
    # async_mode=False -> run each metric synchronously so a slow local model
    # does not trip DeepEval's async-gather timeout.
    metrics = [
        AnswerRelevancyMetric(threshold=_THRESHOLD, model=_JUDGE, async_mode=False),
        GEval(
            name="Correctness",
            criteria=(
                "Determine whether the actual output is factually correct and "
                "semantically equivalent to the expected output. Minor wording "
                "differences are acceptable; contradicting or missing key facts "
                "is not."
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            threshold=_THRESHOLD,
            model=_JUDGE,
            async_mode=False,
        ),
    ]
    if _FULL_METRICS:
        metrics += [
            FaithfulnessMetric(threshold=_THRESHOLD, model=_JUDGE, async_mode=False),
            HallucinationMetric(threshold=0.5, model=_JUDGE, async_mode=False),
        ]
    return metrics


@pytest.mark.parametrize(
    "golden",
    _GOLDEN,
    ids=[g["input"][:50] for g in _GOLDEN],
)
def test_rag_agent(golden):
    result = _AGENT.answer(golden["input"])
    test_case = LLMTestCase(
        input=golden["input"],
        actual_output=result.answer,
        expected_output=golden["expected_output"],
        retrieval_context=result.retrieval_context,
        # HallucinationMetric compares against `context` (ground-truth docs).
        context=result.retrieval_context,
    )
    assert_test(test_case, _metrics())
