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
_REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
_REPORTS = []


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


def _print_case_details(test_case):
    print("\n" + "=" * 80)
    print("QUESTION")
    print(test_case.input)
    print("\nRETRIEVED CONTEXT")
    for index, context in enumerate(test_case.retrieval_context, start=1):
        print("\n--- context chunk {} ---".format(index))
        print(context)
    print("\nACTUAL ANSWER")
    print(test_case.actual_output)
    print("\nEXPECTED ANSWER")
    print(test_case.expected_output)


def _measure_and_print_metrics(test_case, metrics):
    failures = []
    metric_results = []
    print("\nMETRIC SCORES")
    for metric in metrics:
        metric.measure(test_case)
        name = getattr(metric, "name", metric.__class__.__name__)
        score = getattr(metric, "score", None)
        threshold = getattr(metric, "threshold", None)
        reason = getattr(metric, "reason", None)
        is_successful = getattr(metric, "is_successful", None)
        passed = is_successful() if callable(is_successful) else True
        metric_results.append(
            {
                "name": name,
                "score": score,
                "threshold": threshold,
                "passed": passed,
                "reason": reason,
            }
        )
        print("- {}: score={}, threshold={}, passed={}".format(name, score, threshold, passed))
        if reason:
            print("  reason: {}".format(reason))
        if not passed:
            failures.append(name)
    return metric_results, failures


def _record_report(test_case, metric_results):
    _REPORTS.append(
        {
            "question": test_case.input,
            "retrieved_context": test_case.retrieval_context,
            "actual_answer": test_case.actual_output,
            "expected_answer": test_case.expected_output,
            "metrics": metric_results,
        }
    )


def _write_reports():
    _REPORTS_DIR.mkdir(exist_ok=True)
    json_path = _REPORTS_DIR / "rag_eval_report.json"
    markdown_path = _REPORTS_DIR / "rag_eval_report.md"
    json_path.write_text(json.dumps(_REPORTS, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(_format_markdown_report(), encoding="utf-8")
    print("\nEvaluation reports written:")
    print("- {}".format(json_path))
    print("- {}".format(markdown_path))


def _format_markdown_report():
    lines = ["# RAG Evaluation Report", ""]
    lines.append("Total cases: {}".format(len(_REPORTS)))
    lines.append("")
    for index, report in enumerate(_REPORTS, start=1):
        lines.append("## Case {}".format(index))
        lines.append("")
        lines.append("### Question")
        lines.append(report["question"])
        lines.append("")
        lines.append("### Retrieved Context")
        for context_index, context in enumerate(report["retrieved_context"], start=1):
            lines.append("#### Context Chunk {}".format(context_index))
            lines.append("```text")
            lines.append(context)
            lines.append("```")
            lines.append("")
        lines.append("### Actual Answer")
        lines.append(report["actual_answer"])
        lines.append("")
        lines.append("### Expected Answer")
        lines.append(report["expected_answer"])
        lines.append("")
        lines.append("### Metric Scores")
        lines.append("| Metric | Score | Threshold | Passed |")
        lines.append("|---|---:|---:|---|")
        for metric in report["metrics"]:
            lines.append(
                "| {} | {} | {} | {} |".format(
                    metric["name"],
                    metric["score"],
                    metric["threshold"],
                    metric["passed"],
                )
            )
        lines.append("")
        for metric in report["metrics"]:
            if metric["reason"]:
                lines.append("**{} reason:** {}".format(metric["name"], metric["reason"]))
                lines.append("")
    return "\n".join(lines)


def pytest_sessionfinish(session, exitstatus):
    if _REPORTS:
        _write_reports()


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
    _print_case_details(test_case)
    metric_results, failures = _measure_and_print_metrics(test_case, _metrics())
    _record_report(test_case, metric_results)
    if failures:
        pytest.fail("Failed metrics: {}".format(", ".join(failures)))
