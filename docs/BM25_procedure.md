一、BM25 核心原理（Agent 场景价值）
BM25 是基于 TF-IDF 优化的概率检索模型，解决了 TF-IDF 词频无限增长、长文档权重失衡的问题，适合 Agent 做精确关键词匹配、实体 / 术语检索、冷启动无标注场景。
1. 评分公式（Okapi BM25）
Score(Q,D)=∑ 
i=1
n
​
 IDF(q 
i
​
 )⋅ 
f 
i
​
 +k 
1
​
 ⋅(1−b+b⋅ 
avgdl
∣D∣
​
 )
f 
i
​
 ⋅(k 
1
​
 +1)
​
 
IDF：逆文档频率，稀有词权重更高
f_i：查询词在文档中的词频（TF）
k1：词频饱和因子（默认 1.2），控制词频增长上限
b：长度归一化因子（默认 0.75），平衡长短文档权重
avgdl：语料库平均文档长度
2. Agent 场景优势
速度极快：纯 CPU 计算、毫秒级响应，适合实时对话
可解释：得分透明，便于调试与关键词权重调整
轻量：无需 GPU / 训练，适合边缘 / 低成本部署
互补向量：擅长精确匹配，弥补向量检索语义模糊、关键词漏检的问题

三、Milvus 2.5+ 内置 BM25 实现（本项目采用方案）

### 1. 技术选型

| 方案 | 说明 | 优势 | 劣势 |
|------|------|------|------|
| **Milvus 内置 BM25** | Milvus 2.5+ 内置 Function | 无需额外计算、自动生成、简化架构 | 依赖 Milvus 版本 |
| 自定义 BM25 | 使用 rank_bm25 库 | 灵活可控 | 计算开销、维护成本 |

**本项目选择**: Milvus 内置 BM25 Function

### 2. 版本要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Milvus Server | >= 2.5.10 | 支持 BM25 Function 和 nullable sparse vector |
| pymilvus | >= 2.5.0 | 支持 FunctionType.BM25 |
| 分词器 | 内置 chinese | 支持中英文混合文档 |

### 3. Collection Schema 配置

```python
from pymilvus import DataType, Function, FunctionType

# 1. text 字段启用中文分词器
schema.add_field(
    field_name="text",
    datatype=DataType.VARCHAR,
    max_length=65535,
    enable_analyzer=True,              # 启用分词器
    analyzer_params={"type": "chinese"}, # 中文分词
    enable_match=True,                  # 支持文本匹配过滤
)

# 2. text_sparse 字段（BM25 稀疏向量）
schema.add_field(
    field_name="text_sparse",
    datatype=DataType.SPARSE_FLOAT_VECTOR,
)

# 3. BM25 Function 自动生成 sparse vector
bm25_function = Function(
    name="bm25_text_to_sparse",
    function_type=FunctionType.BM25,
    input_field_names=["text"],
    output_field_names=["text_sparse"],
)
schema.add_function(bm25_function)
```

**关键配置说明**:
- `enable_analyzer=True`: 必须启用，否则 BM25 Function 无法工作
- `analyzer_params={"type": "chinese"}`: 支持中文分词，也支持 "english"
- `enable_match=True`: 启用后支持 `TEXT_MATCH` 表达式过滤
- 分词器配置在 collection 创建后**无法修改**

### 4. 索引创建

```python
# BM25 索引参数
index_params.add_index(
    field_name="text_sparse",
    index_type="SPARSE_WAND",           # 稀疏向量专用索引
    index_name="text_sparse_index",
    metric_type="BM25",                 # BM25 度量类型
    params={
        "bm25_k1": 1.5,                 # 词频饱和因子
        "bm25_b": 0.8,                  # 长度归一化因子
    }
)
```

### 5. 参数配置（本项目）

| 参数 | 值 | 说明 |
|------|-----|------|
| k1 | 1.5 | 词频饱和因子，适用于混合语料（技术文档 + 问答） |
| b | 0.8 | 强归一化，确保长短文档公平竞争 |
| RRF k | 60 | Reciprocal Rank Fusion 参数 |

**参数调优依据**:
- 文档类型：技术文档（PDF）+ 问答
- 平均 chunk 大小：约 210 tokens
- 语言：中英混合

### 6. BM25 搜索

```python
# BM25 搜索：直接传入查询文本
results = client.search(
    collection_name="documents",
    data=["BM25 查询文本"],  # 直接传入文本，Milvus 自动处理
    anns_field="text_sparse",
    limit=10,
    output_fields=["pk", "text", "source"]
)
```

**注意**: Milvus 内置 BM25 会自动将查询文本转换为 sparse vector，无需手动处理。

### 7. 混合检索（Dense + Sparse）

```python
from pymilvus import AnnSearchRequest, RRFRanker

# Dense 向量搜索请求
request_dense = AnnSearchRequest(
    data=[query_embeddings],
    anns_field="text_dense",
    param={"metric_type": "IP", "params": {"nprobe": 10}},
    limit=top_k
)

# BM25 搜索请求
request_bm25 = AnnSearchRequest(
    data=[query_text],  # 直接传入文本
    anns_field="text_sparse",
    param={"metric_type": "BM25"},
    limit=top_k
)

# RRF 融合
ranker = RRFRanker(k=60)

# 执行混合搜索
results = client.hybrid_search(
    collection_name="documents",
    reqs=[request_dense, request_bm25],
    ranker=ranker,
    limit=top_k,
    output_fields=["pk", "text", "source"]
)
```

### 8. API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/milvus/search/bm25/` | POST | BM25 文本搜索 |
| `/api/v1/milvus/search/hybrid/` | POST | 混合检索（Dense + Sparse） |

**BM25 搜索请求示例**:
```json
POST /api/v1/milvus/search/bm25/
{
    "collection_name": "documents",
    "query_text": "向量数据库 BM25",
    "top_k": 10,
    "output_fields": ["pk", "text", "source"]
}
```

**混合检索请求示例**:
```json
POST /api/v1/milvus/search/hybrid/
{
    "collection_name": "documents",
    "query_text": "向量数据库 BM25",
    "query_vectors": {
        "text_dense": [0.1, 0.2, ...]
    },
    "top_k": 10,
    "include_sparse": true,
    "rrf_k": 60
}
```

### 9. 重建 Collection

如需为现有数据启用 BM25，需要重建 collection：

```bash
# 使用 Django management command
python manage.py rebuild_collection --collection documents

# 或手动执行
# 1. 删除旧 collection
# 2. 使用新 schema 创建 collection（含 BM25 Function）
# 3. 创建索引
# 4. 重新运行 pipeline 导入数据
```

**注意**: Milvus 内置 BM25 会自动从 `text` 字段生成 sparse vector，插入数据时无需提供 `text_sparse` 字段。

---

二、Agent Chat 工程中 BM25 的标准流程（RAG 架构）
1. 整体架构（三级 RAG）
plaintext
用户提问 → 预处理（分词/停用词） → BM25召回（Top-50~100） → 向量重排/混合融合 → Top-5~10上下文 → LLM生成 → Agent响应
BM25 定位：第一级召回，做 "广度筛选"，快速缩小候选池
向量 / 重排：第二级精排，做 "深度语义匹配"
2. 工程步骤（全链路）
（1）数据预处理（关键：中文适配）
文本分块：按 512~1024 字符切分知识库文档，保留段落完整性
分词：英文用空格；中文用 jieba、THULAC 等，必须自定义分词（BM25 库默认空格分词不支持中文）
清洗：小写、去停用词、去特殊符号、词干化（英文）
（2）BM25 索引构建（离线）
建立倒排索引：词 → 文档 ID / 位置映射，O (logN) 检索
计算 IDF、文档长度、平均长度等统计量
（3）检索服务（在线）
接收 Agent 查询 → 分词 → 计算 BM25 得分 → 返回 Top-K 文档
与 Agent 状态机 / 工作流（如 LangGraph）集成，作为检索节点
（4）上下文拼接与生成
将 BM25 召回结果与向量结果融合 → 构造 Prompt → 调用 LLM 生成答案