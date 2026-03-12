# 本地测试开发环境配置

- 我们的开发测试环境在macos上运行，所以需要安装docker，尽量自己手动操作，以免claude console操作的命令错误，和这些环境冲突。

## 版本要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Milvus | >= 2.5.10 | 支持 BM25 Function 和 sparse vector |
| pymilvus | >= 2.5.0 | 支持 FunctionType.BM25 |
| etcd | v3.5.5 | 与 Milvus 2.5 兼容 |
| minio | RELEASE.2023-03-20T20-16-18Z | 与 Milvus 2.5 兼容 |

**重要**: Milvus 2.5+ 版本支持内置 BM25 Function，可自动从文本生成 sparse vector，无需额外计算。

## Milvus 服务
- MILVUS url: localhost:19530
- attu url: localhost:8080

## celery
- celery url: 待定

## postgresSQL
- url: localhost:5432

## attu 服务启动命令(需要先启动 milvus 服务)
- docker run -d -p 8080:3000 -e MILVUS_URL=172.19.0.4:19530 --name attu zilliz/attu:v2.6

## Milvus BM25 功能说明

Milvus 2.5+ 内置 BM25 Function，支持：
- 自动从 `text` 字段生成 sparse vector
- 中英文分词（配置 `analyzer_params={"type": "chinese"}`）
- BM25 搜索和混合检索（Dense + Sparse）

详见: `docs/BM25_procedure.md`

