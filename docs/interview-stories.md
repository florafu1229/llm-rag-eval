# AI 测试与 RAG 评测面试故事

这份文档准备三个面试里常用的项目故事:

- 如何构建 golden dataset
- 如何发现 hallucination
- 如何定位一次 RAG 评测失败

这些内容可以帮助你在面试中把本项目讲清楚。

## 故事 1: 如何构建 Golden Dataset

### 面试官可能会问

```text
你是怎么为 RAG 评测项目构建 golden dataset 的?
```

### 简短回答

我先从知识库出发,梳理核心概念和真实用户可能会问的问题,然后为每个问题写出有文档依据的 expected answer,最后整理到 `data/golden.json`。数据集里不只包含基础事实题,还包含概念对比题、边界问题和负向问题,用来同时测试正确性和反幻觉能力。

### STAR 版本

**Situation 背景:**

我需要一种可靠方式来评估一个 RAG Agent 是否能基于 Kubernetes Markdown 知识库正确回答问题。

**Task 任务:**

我要构建一个小而有代表性的 golden dataset,让它可以驱动自动化测试,并在模型、prompt 或检索逻辑变化时发现质量回归。

**Action 行动:**

我阅读知识库内容,选出 Pods、Services、Deployments、调度、命名空间、存储等核心概念。然后围绕这些概念设计用户视角的问题,并写出简洁的 expected answer。每个 expected answer 都必须能从知识库中找到依据。我还加入了一些容易混淆的问题,比如 Pod 和 Node 的区别、Service 的作用等。

**Result 结果:**

最终 `data/golden.json` 成为评测套件的标准输入。每一条 golden case 都会被 pytest 转成一个独立测试,经过 RAG Agent 回答,再由 DeepEval 指标评估 relevancy、correctness 等质量指标。

### 可以提到的技术细节

- 数据集放在 `data/golden.json`。
- 每个 case 包含 `input` 和 `expected_output`。
- `pytest.mark.parametrize` 会把每一条 JSON 记录变成独立测试。
- expected answer 是语义标准答案,不是字符串精确匹配。
- 后续只要往 JSON 里新增 case,测试覆盖率就能扩展。

### 面试加分点

- Golden dataset 必须基于 source document,不能凭空写。
- Expected answer 要包含关键事实,不能太模糊。
- 数据集质量直接决定评测质量。
- 负向问题很重要,可以测试模型是否会在 context 不足时产生幻觉。

## 故事 2: 如何发现 Hallucination

### 面试官可能会问

```text
你会怎么检测 RAG 系统里的 hallucination?
```

### 简短回答

我不会只看答案是否“听起来正确”,而是把答案和 retrieved context 对比。如果答案里出现了 context 没有支持的事实,我就把它归类为 hallucination 或 faithfulness 问题。在本项目里,我用 DeepEval 的 Faithfulness 和 Hallucination 指标,并且在报告中输出 retrieved context、actual answer、expected answer、metric score 和 judge reason,方便人工复核。

### STAR 版本

**Situation 背景:**

RAG Agent 即使在检索上下文不足时,也可能生成非常流畅、看起来可信的回答。这会带来 unsupported claim 或编造事实的风险。

**Task 任务:**

我需要判断模型到底是基于 Kubernetes 知识库回答,还是凭自己的预训练知识或猜测在回答。

**Action 行动:**

我让 `RagAgent.answer()` 同时返回生成答案和 `retrieval_context`。在测试中,我把 `actual_output`、`expected_output`、`retrieval_context` 和 `context` 一起放进 DeepEval 的 `LLMTestCase`。当设置 `FULL_METRICS=1` 时,测试会额外运行 Faithfulness 和 Hallucination 指标。我还加了 Markdown/JSON 报告,让每次评测都有可追踪证据。

**Result 结果:**

当模型产生 unsupported answer 时,报告可以快速定位问题。我能看到 retrieved context 到底有没有包含相关事实,也能看到 judge reason 是否指出了矛盾或无依据内容。

### 示例解释

如果知识库只说 Service 给 Pods 提供稳定网络入口,但模型回答说 Service 会自动扩容 Pods,这就是 hallucination。因为这个说法没有 retrieved context 支持。

### 可以提到的技术细节

- `RagAgent.answer()` 返回 `retrieval_context`。
- `LLMTestCase.context` 设置为检索出来的 chunks。
- `FULL_METRICS=1` 会启用 Faithfulness 和 Hallucination 检查。
- `reports/rag_eval_report.md` 会记录 context 和 judge reason。

### 面试加分点

- Hallucination 要相对于 provided context 判断。
- 看起来正确的答案也可能不 faithful。
- Debug report 很重要,因为 metric score 本身不够解释问题。
- 小模型 judge 可能不稳定,所以需要结合人工复核。

## 故事 3: 如何定位一次 RAG 评测失败

### 面试官可能会问

```text
如果一个 RAG evaluation test 失败了,你怎么 debug?
```

### 简短回答

我会分层定位:先看 golden question 和 expected answer,再看 retrieved context,然后看 actual answer,最后看 metric score 和 judge reason。这样可以把失败归类成 retrieval failure、generation failure、judge failure 或 dataset failure。

### STAR 版本

**Situation 背景:**

某个 RAG evaluation case 在 pytest 中失败,显示有指标没有达到 threshold。

**Task 任务:**

我要判断失败原因到底是检索错了、模型生成错了、judge 判错了,还是 golden dataset 本身写得不好。

**Action 行动:**

我在测试里加入详细输出和报告生成。每个 case 都会打印和记录 question、retrieved context、actual answer、expected answer、metric scores 和 judge reasons。然后我按下面顺序检查报告:

1. Question 是否清楚。
2. Retrieved context 是否包含必要事实。
3. Actual answer 是否正确使用了 context。
4. Actual answer 和 expected answer 是否语义一致。
5. Metric score 和 judge reason 是否合理。
6. 把失败归类。

**Result 结果:**

这个流程让失败变得可执行。如果 retrieval 错了,就改 chunking 或 retriever。如果 generation 错了,就改 prompt 或换模型。如果 judge 错了,就调整 judge model 或 GEval criteria。如果 dataset 错了,就重写 expected answer。

### 失败分类

#### Retrieval Failure: 检索失败

表现:

- Retrieved chunks 和问题无关。
- Expected facts 没有出现在 context 里。
- 模型因为 context 太弱而回答 “I don't know”。

修复:

- 改进 chunking。
- 增大 top-k。
- 补充知识库内容。
- 使用 embedding retrieval 或 reranking。

#### Generation Failure: 生成失败

表现:

- Context 是正确的,但答案不完整或错误。
- 模型忽略 prompt 约束。
- 信息不足时没有拒答。

修复:

- 改进 system prompt。
- 使用更强 agent model。
- 降低 temperature。
- 增加回答格式要求。

#### Judge Failure: 裁判失败

表现:

- 人工看答案是对的,但 judge 判失败。
- Judge reason 和 actual answer 矛盾。
- 每次运行分数波动大。

修复:

- 使用更强 judge model。
- 调整 threshold。
- 改进 GEval criteria。
- 尽量让 judge model 和 agent model 分开。

#### Dataset Failure: 数据集失败

表现:

- Expected answer 太模糊或太严格。
- Expected answer 包含知识库没有的事实。
- Question 本身有歧义。

修复:

- 重写 expected answer。
- 把大问题拆成小问题。
- 补充 source material。

## 30 秒项目介绍

```text
我做了一个本地 RAG 自动评测框架,使用 Python、pytest、DeepEval 和 Ollama。系统会读取 golden Q&A 数据集,从 Kubernetes 知识库中检索相关 context,让本地 LLM 基于 context 回答,再用 LLM-as-a-judge 指标评估 relevancy、correctness、faithfulness 和 hallucination。我还增加了 Markdown/JSON 报告,输出 retrieved context、actual answer、expected answer、metric scores 和 judge reasoning,方便定位 RAG 失败原因。
```

## 2 分钟项目介绍

```text
这个项目是一个面向 RAG 应用的 AI 测试 demo。我想模拟 AI Test Engineer 如何验证一个 LLM 应用,所以创建了一个小型 Kubernetes 知识库和 golden Q&A 数据集。RAG Agent 会从知识库中检索 top-k chunks,然后把 context 发给 OpenAI-compatible endpoint。我的本地环境使用 Ollama,但同一套代码也可以接 OpenAI、Azure OpenAI、vLLM 或其他兼容网关。

评测部分我用了 pytest 和 DeepEval。每个 golden question 都会成为一个 parametrized test case。默认测试 Answer Relevancy 和 Semantic Correctness,也可以通过 FULL_METRICS=1 启用 Faithfulness 和 Hallucination。因为本地小模型 judge 可能慢且不稳定,所以我把 threshold 做成可配置,并加了详细报告。

这个项目最重要的点是 debug workflow。每个 case 的报告都会记录 question、retrieved context、actual answer、expected answer、metric scores 和 judge reason。这样可以把失败分类成 retrieval issue、generation issue、judge issue 或 dataset issue。这和真实生产环境里的 LLM regression testing 很接近。
```
