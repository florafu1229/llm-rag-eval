"""A minimal, dependency-free retriever over Markdown knowledge files.

The knowledge base is split into chunks on Markdown headings. Retrieval uses a
simple keyword-overlap score. This keeps the demo self-contained (no embedding
model or vector DB required) while still exercising the full RAG shape:

    query -> retrieve top-k chunks -> feed as context to the LLM.

Swapping this out for a real embedding retriever (FAISS/Chroma) later does not
change the agent or the evaluation code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

_STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "and", "or", "in", "on", "for",
    "what", "which", "who", "how", "does", "do", "it", "its", "that", "this",
    "with", "by", "as", "at", "be", "was", "were", "used", "use", "each",
}


@dataclass
class Chunk:
    title: str
    text: str

    @property
    def content(self) -> str:
        return f"{self.title}\n{self.text}".strip()


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def load_chunks(knowledge_dir: str | Path) -> List[Chunk]:
    """Load every ``*.md`` file under *knowledge_dir* and split on headings."""
    knowledge_dir = Path(knowledge_dir)
    chunks: List[Chunk] = []
    for md_file in sorted(knowledge_dir.glob("*.md")):
        raw = md_file.read_text(encoding="utf-8")
        # Split on Markdown headings while keeping the heading with its body.
        parts = re.split(r"(?m)^(#{1,6}\s+.*)$", raw)
        # re.split with a capture group yields: [pre, heading, body, heading, body, ...]
        current_title = md_file.stem
        buffer: List[str] = []

        def flush(title: str, body_lines: List[str]) -> None:
            body = "\n".join(body_lines).strip()
            if body:
                chunks.append(Chunk(title=title.strip(), text=body))

        i = 0
        # Handle any preamble before the first heading.
        if parts and not parts[0].lstrip().startswith("#"):
            flush(current_title, [parts[0]])
            parts = parts[1:]
        while i + 1 < len(parts):
            heading = parts[i]
            body = parts[i + 1]
            flush(heading.lstrip("# ").strip(), [body])
            i += 2
    return chunks


class KeywordRetriever:
    """Retrieve the most relevant knowledge chunks for a query."""

    def __init__(self, knowledge_dir: str | Path):
        self.chunks = load_chunks(knowledge_dir)
        if not self.chunks:
            raise ValueError(f"No knowledge chunks found in {knowledge_dir}")

    def retrieve(self, query: str, k: int = 3) -> List[str]:
        query_terms = set(_tokenize(query))
        scored: List[tuple[float, Chunk]] = []
        for chunk in self.chunks:
            chunk_terms = _tokenize(chunk.content)
            if not chunk_terms:
                continue
            overlap = sum(1 for t in chunk_terms if t in query_terms)
            # Normalize slightly by chunk length to avoid always picking the biggest.
            score = overlap / (1 + 0.01 * len(chunk_terms))
            if overlap > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [c.content for _, c in scored[:k]]
        # Fallback: if nothing matched, return the first k chunks so the agent
        # still has some grounding context.
        return top or [c.content for c in self.chunks[:k]]
