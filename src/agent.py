"""The knowledge agent (the system under test).

A tiny RAG agent: given a question, it retrieves the most relevant chunks from
the knowledge base and asks the LLM to answer strictly from that context.
Returning both the answer and the retrieval context is what lets DeepEval score
faithfulness / hallucination / context relevancy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .llm import chat_complete
from .retriever import KeywordRetriever

_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"

_SYSTEM_PROMPT = """You are an assistant that answers technical questions using \
only the provided reference material.

Answer the QUESTION using ONLY the information in CONTEXT. If the answer is not
contained in the context, reply exactly: "I don't know based on the provided \
context." Be concise and factual.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""


@dataclass
class AgentResult:
    question: str
    answer: str
    retrieval_context: List[str] = field(default_factory=list)


class RagAgent:
    def __init__(self, k: int = 3):
        self.retriever = KeywordRetriever(_KNOWLEDGE_DIR)
        self.k = k

    def answer(self, question: str) -> AgentResult:
        context_chunks = self.retriever.retrieve(question, k=self.k)
        prompt = _SYSTEM_PROMPT.format(
            context="\n\n---\n\n".join(context_chunks),
            question=question,
        )
        answer = chat_complete(prompt).strip()
        return AgentResult(
            question=question,
            answer=answer,
            retrieval_context=context_chunks,
        )
