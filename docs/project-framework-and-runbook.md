# 项目框架与运行手册

这份文档说明本项目的整体框架、运行方式、关键代码路径和排障方法。

## 1. 项目目标

本项目是一个 AI 测试 / RAG 评测作品集项目。

它展示如何:

- 用 Markdown 文档构建一个简单知识库。
- 用 golden Q&A dataset 作为测试输入。
- 搭建一个最小 RAG Agent。
- 使用 pytest + DeepEval 做自动化 LLM 评测。
- 使用 Ollama 或任何 OpenAI-compatible endpoint。
- 生成 Markdown 和 JSON 评测报告。

## 2. 总体架构

```text
data/golden.json
      ↓
tests/test_rag_eval.py
      ↓
RagAgent
      ↓
KeywordRetriever → data/knowledge/kubernetes.md
      ↓
OpenAI-compatible API → Ollama / OpenAI / Azure / vLLM
      ↓
LLM 生成 actual answer
      ↓
DeepEval metrics + CustomJudge
      ↓
pytest pass/fail
      ↓
reports/rag_eval_report.md
reports/rag_eval_report.json
```

## 3. 目录结构

```text
llm-rag-eval/
├── data/
│   ├── knowledge/kubernetes.md
│   └── golden.json
├── docs/
│   ├── llm-evaluation-and-dataset-design.md
│   ├── interview-stories.md
│   └── project-framework-and-runbook.md
├── src/
│   ├── retriever.py
│   ├── agent.py
│   └── llm.py
├── tests/
│   └── test_rag_eval.py
├── reports/
│   ├── rag_eval_report.md
│   └── rag_eval_report.json
├── run_demo.py
├── requirements.txt
├── .env.example
└── README.md
```

## 4. 核心组件说明

### 4.1 `data/knowledge/kubernetes.md`

这是知识库,也是 RAG 的 source of truth。

RAG Agent 应该只基于这里的内容回答问题。如果答案无法从这里找到,理想行为是回答:

```text
I don't know based on the provided context.
```

### 4.2 `data/golden.json`

这是 golden dataset。

每个 case 包含:

```json
{
  "input": "用户问题",
  "expected_output": "标准答案"
}
```

测试会把每一条 case 转成一个独立 pytest case。

### 4.3 `src/retriever.py`

这是最小版 retriever。

当前实现是 `KeywordRetriever`:

1. 读取 `data/knowledge/*.md`。
2. 按 Markdown heading 切成 chunks。
3. 对 question 和 chunk 做 keyword overlap。
4. 返回 top-k 相关 chunks。

这个实现没有依赖 embedding model 或 vector DB,适合 demo 和本地运行。

后续可以替换成:

- Chroma
- FAISS
- Qdrant
- Milvus
- reranker

### 4.4 `src/agent.py`

这是 RAG Agent,也就是被测试对象。

主要流程:

1. 接收 question。
2. 调用 `KeywordRetriever.retrieve()` 找 top-k chunks。
3. 把 chunks 拼成 context。
4. 构造 prompt。
5. 调用 `chat_complete()`。
6. 返回 answer 和 retrieval_context。

关键点:

```text
RagAgent.answer(question) → AgentResult(answer, retrieval_context)
```

### 4.5 `src/llm.py`

这里封装 LLM 调用。

包含两部分:

- `chat_complete()`: 给 Agent 生成答案。
- `CustomJudge`: 给 DeepEval 当 judge model。

它通过 OpenAI-compatible API 工作,所以可以接:

- Ollama
- OpenAI
- Azure OpenAI
- vLLM
- 其他兼容网关

### 4.6 `tests/test_rag_eval.py`

这是最核心的评测入口。

它负责:

1. 读取 `data/golden.json`。
2. 用 `pytest.mark.parametrize` 生成测试 case。
3. 调用 `RagAgent.answer()`。
4. 构造 `LLMTestCase`。
5. 调用 DeepEval metrics 打分。
6. 输出 question/context/answer/score。
7. 生成 Markdown 和 JSON 报告。

默认评测指标:

- Answer Relevancy
- Correctness / GEval

设置 `FULL_METRICS=1` 后额外启用:

- Faithfulness
- Hallucination

## 5. 本地运行步骤

### 5.1 创建虚拟环境

推荐使用项目内 `.venv`。

```bash
cd ~/llm-rag-eval
python3.12 -m venv .venv
source .venv/bin/activate
```

如果你用 Python 3.11,也可以:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 5.2 安装依赖

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

国内网络可以使用清华源:

```bash
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 5.3 配置 Ollama

确认 Ollama 有模型:

```bash
ollama list
```

如果没有,先拉一个小模型:

```bash
ollama pull qwen2.5:1.5b
```

复制环境变量文件:

```bash
cp .env.example .env
```

编辑 `.env`:

```dotenv
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
AGENT_MODEL=qwen2.5:1.5b
JUDGE_MODEL=qwen2.5:1.5b
```

说明:

- `AGENT_MODEL`: 负责回答问题的模型。
- `JUDGE_MODEL`: 负责给答案打分的模型。
- 旧 Mac 建议先用 `qwen2.5:1.5b`。

### 5.4 先跑 offline demo

```bash
python run_demo.py
```

这个命令不会调用 LLM,只验证 retrieval 是否正常。

它会输出:

- 加载了多少 knowledge chunks
- 每个 golden question 检索到了哪些 chunks
- top chunk 是否和 expected answer 有词重叠

### 5.5 跑完整评测

```bash
python -m pytest tests/test_rag_eval.py -s -vv
```

参数说明:

- `python -m pytest`: 确保用当前 Python 环境里的 pytest。
- `-s`: 显示 print 输出。
- `-vv`: 输出更详细的 case 名称。

### 5.6 跑完整四类指标

默认只跑两个较轻指标。要启用 Faithfulness 和 Hallucination:

```bash
FULL_METRICS=1 python -m pytest tests/test_rag_eval.py -s -vv
```

旧 Mac 上这个会慢很多。

### 5.7 调整 threshold

默认 threshold 是 `0.5`。

提高标准:

```bash
EVAL_THRESHOLD=0.7 python -m pytest tests/test_rag_eval.py -s -vv
```

如果 judge model 很弱,不要一开始设置太高。

## 6. 运行后看哪里

测试运行时会直接打印:

```text
QUESTION
RETRIEVED CONTEXT
ACTUAL ANSWER
EXPECTED ANSWER
METRIC SCORES
```

测试结束后会生成:

```text
reports/rag_eval_report.md
reports/rag_eval_report.json
```

打开 Markdown 报告:

```bash
open reports/rag_eval_report.md
```

报告里能看到:

- 问题
- 检索上下文
- 模型实际答案
- 标准答案
- 每个 metric 的 score
- threshold
- 是否通过
- judge reason

## 7. 一次测试的完整执行链路

```text
pytest 启动
  ↓
读取 data/golden.json
  ↓
取出一个 golden case
  ↓
RagAgent.answer(input)
  ↓
KeywordRetriever 检索 top-k chunks
  ↓
拼接 context + question 成 prompt
  ↓
调用 Ollama AGENT_MODEL
  ↓
得到 actual answer
  ↓
构造 DeepEval LLMTestCase
  ↓
CustomJudge 调用 Ollama JUDGE_MODEL
  ↓
DeepEval metric 计算 score
  ↓
打印详情并写入 reports
  ↓
如果所有 metric 达标 → pass
否则 → fail
```

## 8. 常见问题排查

### 8.1 `pytest: command not found`

原因:

- 没有激活 `.venv`
- 或依赖没装到当前 Python

解决:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest tests/test_rag_eval.py -s -vv
```

### 8.2 测试一直卡在第一个 case

原因通常是 Ollama 本地推理慢。

排查:

```bash
ollama ps
```

如果看到 CPU 很高,说明模型正在运行,不是死机。

解决:

- 先用 `qwen2.5:1.5b`。
- 只保留一个 case。
- 不启用 `FULL_METRICS=1`。
- 等待几分钟。

### 8.3 DeepEval judge 分数不稳定

原因:

- 小模型做 judge 能力有限。
- 本地模型可能输出格式不稳定。

解决:

- 使用更强 judge model。
- 降低 `EVAL_THRESHOLD`。
- 看 judge reason,不要只看 score。
- 必要时人工复核。

### 8.4 Answer 看起来对,但 metric fail

可能原因:

- Judge failure
- Expected answer 太严格
- GEval criteria 不够清楚
- 小模型 judge 判断错误

处理:

1. 打开 `reports/rag_eval_report.md`。
2. 对比 actual answer 和 expected answer。
3. 看 judge reason 是否合理。
4. 如果 judge 错,换 judge model 或调 threshold。

### 8.5 Answer 不对

先判断是哪一类问题:

- context 不对 → retrieval failure
- context 对但 answer 错 → generation failure
- answer 对但 judge 判错 → judge failure
- expected answer 有问题 → dataset failure

## 9. 面试时怎么讲这个项目

可以这样讲:

```text
这个项目模拟了一个真实 RAG 应用的自动化评测流程。我用 Kubernetes Markdown 文档作为知识库,用 golden.json 设计标准问答集。测试时,RAG Agent 先从知识库检索相关 context,再调用 Ollama 本地模型生成答案。随后 DeepEval 使用 judge model 对答案做 relevancy、correctness、faithfulness 和 hallucination 评估。最后 pytest 给出 pass/fail,并生成 Markdown/JSON 报告,帮助定位失败是 retrieval、generation、judge 还是 dataset 问题。
```

## 10. 后续增强方向

可以继续加:

- `MAX_CASES`: 本地只跑前 N 个 case。
- `enabled: false`: JSON 中禁用某些 case。
- latency 统计。
- token usage 统计。
- 多模型对比报告。
- Chroma / FAISS embedding retriever。
- GitHub Actions CI smoke evaluation。
