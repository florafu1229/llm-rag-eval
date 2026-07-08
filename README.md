# llm-rag-eval — LLM/RAG Evaluation Demo (DeepEval)

An end-to-end **AI testing** portfolio project. It builds a small **RAG agent**
that answers questions about **Kubernetes** using a knowledge base, then
**automatically evaluates** the agent's answers with
[DeepEval](https://github.com/confident-ai/deepeval).

The knowledge base is just Markdown, so you can point this at *any* domain by
swapping the files in `data/knowledge/` and the Q&A in `data/golden.json` —
none of the pipeline or evaluation code changes.

It demonstrates the skills an *AI / LLM Test Engineer* is hired for:

- Turning documentation into a **golden test dataset**
- Building a **RAG pipeline** (retrieve → ground → answer)
- Writing **automated LLM eval** with quality metrics (like unit tests for LLMs)
- Detecting **hallucination**, measuring **faithfulness**, **relevancy**, and **correctness**
- Running it as a **pytest / CI-friendly** suite against any OpenAI-compatible endpoint

## 中文学习文档

- [LLM 评测指标与 Golden Dataset 设计](docs/llm-evaluation-and-dataset-design.md)
- [AI 测试与 RAG 评测面试故事](docs/interview-stories.md)
- [项目框架与运行手册](docs/project-framework-and-runbook.md)

## What gets measured

| Metric | Question it answers |
|--------|---------------------|
| **AnswerRelevancy** | Is the answer on-topic for the question? |
| **Faithfulness** | Is the answer grounded in the retrieved context? |
| **Hallucination** | Does the answer invent/contradict facts vs the context? |
| **Correctness (GEval)** | Does the answer match the golden/expected answer? |

## Project layout

```
llm-rag-eval/
├── data/
│   ├── knowledge/kubernetes.md  # knowledge base (RAG source of truth)
│   └── golden.json              # golden Q&A test dataset
├── src/
│   ├── retriever.py             # keyword retriever over the knowledge base
│   ├── agent.py                 # the RAG agent = system under test
│   └── llm.py                   # OpenAI-compatible client + DeepEval custom judge
├── tests/
│   └── test_rag_eval.py         # DeepEval metric suite (one case per golden Q)
├── docs/                        # Chinese learning notes, runbook, interview stories
├── run_demo.py                  # offline wiring check (no API key needed)
├── requirements.txt
└── .env.example
```

## Setup

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Configure your LLM endpoint
cp .env.example .env           # then edit .env  (Windows: copy .env.example .env)
```

`.env` works with **OpenAI, Azure OpenAI, a local vLLM/Ollama server, or any
OpenAI-compatible gateway** — just set `OPENAI_BASE_URL`, `OPENAI_API_KEY`,
`AGENT_MODEL`, and `JUDGE_MODEL`.

> Tip for a fully local run: start `ollama serve`, pull a model
> (`ollama pull qwen2.5`), and set `OPENAI_BASE_URL=http://localhost:11434/v1`.

## Run

```bash
# Offline: verify retrieval wiring, no tokens spent
python run_demo.py

# Full evaluation with the rich DeepEval report
deepeval test run tests/test_rag_eval.py

# Or as plain pytest
pytest tests/test_rag_eval.py -v
```

### Tuning knobs (env vars)

| Variable | Default | Purpose |
|----------|---------|---------|
| `EVAL_THRESHOLD` | `0.5` | Pass score for each metric. Raise to `0.8` with a strong judge. |
| `FULL_METRICS` | `0` | Set to `1` to also run Faithfulness + Hallucination (slower). |
| `DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE` | `1200` | Per-metric timeout (set in `conftest.py`). |

### Important: the judge model matters

Metrics are scored by an **LLM judge**. A small local judge (e.g.
`qwen2.5:3b` on CPU) is **slow and can score erratically** — it may mark a
correct answer as "missing a key fact" that the answer actually contains.
This is itself a key AI-testing lesson: *your eval is only as trustworthy as
your judge.* For reliable scoring use a stronger judge:

- a larger local model (`ollama pull qwen2.5:7b`, set `JUDGE_MODEL=qwen2.5:7b`), or
- a hosted frontier model via any OpenAI-compatible endpoint.

### Windows note

DeepEval prints emoji; the legacy Windows console can crash with
`UnicodeEncodeError`. `conftest.py` forces UTF-8 output to prevent this.

## How it works

1. `run_demo.py` / the test loads `data/golden.json`.
2. For each question, `RagAgent` retrieves the top-k chunks from
   `data/knowledge/kubernetes.md` and asks the **agent model** to answer *only*
   from that context.
3. The answer + retrieved context + expected answer become a `LLMTestCase`.
4. DeepEval scores each case with the metrics using the **judge model**.
5. A case passes only if every metric clears its threshold (`EVAL_THRESHOLD`).

## Extending it

- **Real vector retrieval**: replace `KeywordRetriever` with FAISS/Chroma +
  embeddings — nothing else changes.
- **More coverage**: add rows to `data/golden.json`.
- **Agent testing**: point the pipeline at a tool-using agent and add
  tool-call / trajectory metrics.
- **Red-teaming**: add adversarial inputs (prompt injection) as extra cases.
- **CI**: run `deepeval test run` in GitHub Actions to gate prompt/model changes.
