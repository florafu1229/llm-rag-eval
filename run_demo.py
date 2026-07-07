"""Offline smoke test - runs WITHOUT any LLM API key.

It exercises the retriever (the RAG "R") for every golden question and prints
which knowledge chunks would be fed to the agent. Use this to verify the
project wiring before spending tokens on a real eval run.

    python run_demo.py
"""

from __future__ import annotations

import json
from pathlib import Path

from src.retriever import KeywordRetriever

ROOT = Path(__file__).resolve().parent
KNOWLEDGE = ROOT / "data" / "knowledge"
GOLDEN = json.loads((ROOT / "data" / "golden.json").read_text(encoding="utf-8"))


def main() -> None:
    retriever = KeywordRetriever(KNOWLEDGE)
    print(f"Loaded {len(retriever.chunks)} knowledge chunks from {KNOWLEDGE}\n")
    for i, g in enumerate(GOLDEN, 1):
        question = g["input"]
        chunks = retriever.retrieve(question, k=2)
        print(f"[{i}] Q: {question}")
        top_titles = [c.splitlines()[0] for c in chunks]
        print(f"    Retrieved chunks: {top_titles}")
        # Naive grounding check: does the top chunk share words with the gold answer?
        gold = g["expected_output"].lower()
        hit = any(
            word in chunks[0].lower()
            for word in gold.split()
            if len(word) > 4
        )
        print(f"    Top chunk overlaps expected answer: {hit}\n")
    print("Offline wiring OK. To run the real eval:")
    print("  1) cp .env.example .env  and fill in your endpoint/keys")
    print("  2) deepeval test run tests/test_rag_eval.py")


if __name__ == "__main__":
    main()
