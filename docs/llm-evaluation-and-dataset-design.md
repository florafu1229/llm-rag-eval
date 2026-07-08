# LLM 评测指标与 Golden Dataset 设计

这份文档总结 AI 测试 / LLM 评测岗位里很重要的两块知识:

- **LLM 评测指标**
- **Golden Dataset 设计**

本文示例基于本项目的 RAG 评测流程: `data/golden.json` + `data/knowledge/kubernetes.md` + `tests/test_rag_eval.py`。

## 1. LLM 评测指标

LLM 评测指标不是只看“答案对不对”,而是从不同角度衡量回答质量。一个好的评测体系不应该只依赖单一指标。

### 1.1 Answer Relevancy: 回答相关性

**它回答的问题:** 模型有没有真正回答用户的问题?

一个回答可能事实正确,但和问题不相关。例如用户问 Kubernetes Pod,模型回答了一堆容器发展历史,内容可能没错,但没有回答问题。

**适合发现:**

- 回答跑题
- 模型没有理解问题
- 回答太泛泛而谈
- 只是复述 context,但没有针对问题作答

**常见失败现象:**

- 回答了相关但不同的概念
- 回答过于宽泛
- 没有覆盖问题里的关键点

### 1.2 Semantic Correctness: 语义正确性

**它回答的问题:** 实际答案和 golden answer 在语义上是否一致?

这不是字符串精确匹配。只要关键事实一致,措辞可以不同。

**适合发现:**

- 模型或 prompt 改动后的质量回归
- 回答是否包含 expected answer 里的关键事实
- 实际输出是否和人工标准答案一致

**常见失败现象:**

- 缺少关键事实
- 和 expected answer 矛盾
- 多问题只回答了一半
- 答案听起来正确,但没有覆盖标准答案要求

### 1.3 Faithfulness: 忠实性 / 上下文一致性

**它回答的问题:** 答案是否忠实于检索出来的 context?

对 RAG 系统来说,Faithfulness 非常重要。因为 RAG 的目标不是让模型凭记忆回答,而是让模型基于提供的文档回答。

**适合发现:**

- 答案里有没有 unsupported claim
- 模型有没有遵守“只基于 context 回答”的指令
- 是 retrieval 问题,还是 generation 问题

**常见失败现象:**

- 答案包含 context 没有的信息
- context 不足时模型仍然猜测
- 答案看起来合理,但无法从 context 追溯依据

### 1.4 Hallucination: 幻觉

**它回答的问题:** 模型是否编造了 context 中没有的事实,或者和 context 矛盾?

在 RAG 评测里,幻觉通常不是指“回答不完美”,而是指模型说出了没有文档依据的内容。

**适合发现:**

- 事实安全问题
- 模型自信编造
- context 不足时没有拒答
- 产品能力、版本号、配置值等被编造

**常见失败现象:**

- 编造配置项或默认值
- 编造不存在的功能
- 错误版本号
- context 没有答案,但模型仍然自信回答

### 1.5 Context Relevancy: 检索上下文相关性

**它回答的问题:** Retriever 找到的 context 是否真的对回答问题有帮助?

这个指标更关注 retrieval 质量,而不是生成质量。

**适合发现:**

- Retriever 找错章节
- Chunk 切分不合理
- Top-k 太小或太大
- Keyword retriever 和 embedding retriever 的差异

**常见失败现象:**

- 检索出来的 chunks 来自错误章节
- 关键 context 缺失
- 包含太多无关 context

### 1.6 Latency / Cost: 延迟和成本

**它回答的问题:** 这个 AI 测试系统是否实际可运行?

AI 测试除了质量指标,也应该关注工程指标。

**可以记录:**

- Agent 回答耗时
- Judge 打分耗时
- 单 case 总耗时
- token 使用量
- 单 case 成本
- pass rate 趋势

## 2. 如何理解评测结果

测试 pass 不代表答案完美,只代表当前答案在当前 judge model 和当前 threshold 下通过。

需要注意:

- 小模型 judge 可能不稳定。
- 弱 judge 可能放过坏答案,也可能错杀好答案。
- threshold 要根据模型能力和业务风险调整。
- metric reason 和 score 一样重要。

推荐读报告顺序:

1. 看 question。
2. 看 retrieved context。
3. 看 actual answer。
4. 对比 expected answer。
5. 看 metric score 和 judge reason。
6. 判断失败属于哪一类。

## 3. Golden Dataset 设计

Golden dataset 是一组人工设计的问题和标准答案,用于评测 AI 系统。

本项目里的 golden dataset 是 `data/golden.json`。

每个 case 类似:

```json
{
  "input": "What is Kubernetes?",
  "expected_output": "Kubernetes is an open-source container orchestration platform..."
}
```

### 3.1 好的 Golden Case 应该满足什么条件

一个好的 golden case 应该是:

- **有依据:** 答案可以在知识库里找到。
- **具体:** 问题有明确答案。
- **可评测:** 人或 judge 可以判断答案是否正确。
- **有代表性:** 接近真实用户会问的问题。
- **稳定:** expected answer 不应该频繁变化。

### 3.2 Dataset 应该覆盖哪些问题类型

一个好的数据集不应该只有简单事实题,应该覆盖多种问题类型。

#### 基础事实题

用于验证核心知识。

```text
What is a Kubernetes Pod?
```

#### 概念对比题

用于检查模型是否理解概念差异。

```text
How is a Deployment different from a StatefulSet?
```

#### 多跳问题

用于检查模型是否能结合多个 context 片段回答。

```text
How do Services and Pods work together to expose an application?
```

#### 边界问题

用于检查模型在信息不足时的行为。

```text
What happens if the requested information is not in the context?
```

#### 负向问题

用于测试拒答和反幻觉能力。

```text
What is the default password for the Kubernetes cluster in this document?
```

如果知识库里没有答案,期望行为应该是:

```text
I don't know based on the provided context.
```

#### 回归问题

用于防止以前出现过的错误再次发生。

```text
以前模型混淆 Pod 和 Node,就加一个专门问两者区别的 case。
```

### 3.3 需要多少 case

可以从小到大:

- **5-10 个:** demo 或本地 smoke test
- **20-50 个:** 有实际参考价值的小型 benchmark
- **100+ 个:** 比较严肃的回归测试集

如果是在旧 Mac 上用 Ollama 本地模型,建议先跑小集合。因为一个 case 可能触发多次 LLM 调用。

### 3.4 Expected Answer 怎么写

Expected answer 应该包含关键事实,但不要要求固定措辞。

好的 expected answer:

```text
A Pod is the smallest deployable unit in Kubernetes. It can contain one or more containers that share networking and storage.
```

不好的 expected answer:

```text
Pod is important.
```

问题:

- 太模糊
- 缺少关键事实
- 不容易判断正确性

### 3.5 Dataset 质量检查清单

新增 case 前检查:

- 答案是否能在知识库中找到?
- 问题是否清晰?
- expected answer 是否包含关键事实?
- 是否和已有 case 重复?
- 是否能发现真实 failure mode?
- 它属于正常题、边界题、负向题,还是回归题?

## 4. RAG 失败分类

当一个 case fail,不要只看 pass/fail,要先分类。

### 4.1 Retrieval Failure: 检索失败

表现:

- retrieved context 不包含正确答案
- 找到了错误章节
- 关键事实缺失

修复方向:

- 改进 chunking
- 增大 top-k
- 改进 retriever scoring
- 补充知识库内容
- 使用 embedding search 或 reranking

### 4.2 Generation Failure: 生成失败

表现:

- context 是对的,但模型回答错了
- 回答不完整
- 没有遵守 prompt

修复方向:

- 改 prompt
- 换更强 agent model
- 增加回答格式要求
- 降低 temperature

### 4.3 Judge Failure: 裁判失败

表现:

- 人看答案是对的,但 judge 判错
- judge reason 和实际答案矛盾
- 分数每次波动较大

修复方向:

- 换更强 judge model
- 调整 GEval criteria
- 降低本地小模型的 threshold
- 人工复核 judge reason

### 4.4 Dataset Failure: 数据集失败

表现:

- expected answer 写得太模糊
- expected answer 包含知识库没有的内容
- 问题本身有歧义

修复方向:

- 重写 expected answer
- 补充 source material
- 把大问题拆成多个小问题

## 5. 本项目下一步可增强点

建议后续增强:

- 支持 `enabled: false`,跳过昂贵 case。
- 支持 `MAX_CASES`,本地只跑少量 case。
- 增加每个 case 的 latency 统计。
- 在 report 中增加 failure classification。
- 用 Chroma 或 FAISS 增加 embedding retriever。
- 加 GitHub Actions,跑一个便宜的 smoke eval。
