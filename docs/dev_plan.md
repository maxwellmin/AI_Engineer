# 我们希望按照下面的顺序来开发各个模块，模块交叉的地方在开发过程中会进行调整：
- 1 方案和评估和开发计划
```
需要阅读CLAUD的文档，并了解其工作原理，并确定开发计划。
需要阅读docs里面的dev_plan.md文件，并确定开发计划。
需要阅读docs里面的architecture确认方案可行，并且对齐好开发思路。
```

- 2 基础搭建
```
按照项目目录架构创建django工程和app，创建数据库，并完成数据库的初始化。
在这个步骤的时候，我会处理一下开发用用到的基础设施和环境变量.
确保我们的开发环境是可用的
（基础设施包括了postgresql, neo4j, milvusdb等相关的服务器，环境变量包括了数据库的连接信息，以及一些开发过程中用到的变量，比如开发环境使用的数据库的密码等等）
我们会在这个步骤确认django正常工作，支撑后面的开发。
```

- 3 用户管理模块
```
用户管理模块包括用户的注册，登录，权限管理等功能。
我们会使用django自带的用户管理模块，并且进行一些扩展。
用户管理模块是整个系统的基础，其他模块都需要依赖用户管理模块来进行用户的认证和授权。
特定功能开发和测试时候我们会使用特殊账号或者方通某些api来进行测试。
```

- 4 document parser模块
```
document parser模块负责文档的上传，解析，存储等功能。
我们会使用一些第三方的库来进行文档的解析，比如pdfminer, docx2txt等。
document parser模块是整个系统的核心模块，其他模块都需要依赖document parser模块来获取文档内容。
这里我们需要建立好文档的元数据，包括文档的id，名称，路径，创建时间，更新时间，大小，类型，状态等。
这里还要根据元数据实现去重模块（文档级别）
```

- 5 object_storage_controller
```
object_storage_controller模块负责文档文件的存储功能。
开发环境使用 MinIO（已在 docker-compose.yml 中配置），生产环境可切换到 AWS S3。
使用 django-storages + boto3 进行集成。
实现文件上传、下载、删除、预签名 URL 等功能。
为 document parser 模块提供文件存储支持。
封装好对应的连接器和方法。
```

- 6 milvus_database_controller
```
milvus_database_controller模块负责向量数据库的增删改查功能。
我们会使用milvus官方提供的python sdk来进行向量数据库的操作。
milvus_database_controller模块是整个系统的核心模块，其他模块都需要依赖milvus_database_controller模块来进行向量的存储和检索。
这里我们需要实现创建向量库，插入数据，搜索数据，删除数据等功能。
封装好对应的连接器和方法。
```

- 7 neo4j_database_controller
```
neo4j_database_controller模块负责关系数据库的增删改查功能。
这里我们需要实现创建数据库，插入数据，搜索数据，删除数据等功能。
neo4j_database_controller模块是整个系统的核心模块，其他模块都需要依赖neo4j_database_controller模块来进行关系的存储和检索。
使用官方的python sdk进行操作
封装好对应的连接器和方法
```

- 8 embedding_module
```
embedding_module模块负责文本的向量化功能。
我们会使用一些第三方的库来进行文本的向量化，比如sentence-transformers等。
embedding_module模块是整个系统的核心模块，其他模块都需要依赖embedding_module模块来进行文本的向量化。
这里我们需要实现文本的向量化功能，并且提供接口供其他模块调用。
封装好对应的连接器和方法。
Service的方式提供给其他模块使用。
```

- 9 document pipeline manager
```
当前面8个步骤完成之后，我们就可以开始编写document pipeline manager模块了。
document pipeline manager模块负责文档的解析，向量化，存储等功能。
pipeline要实现管理
User Upload → Django API → Object Storage Controller (MinIO/S3)
    → Document Parser → Text Chunking
    → Embedding Generation → Milvus Storage
    → Entity Extraction → Neo4j Graph Update
    → PostgreSQL Metadata Storage
整个流过程中的状态的跟踪和记录
最终我们会提供一个上传结构到api测，测试的时候会调用这个api，然后用工具来进行测试，上传些文档上来。
```

- 10 document rag search  module
```
这个模块我们将实现文档的RAG搜索功能。
RAG搜索功能包括查询，向量搜索，上下文组装，LLM生成等步骤的实现。
整个数据流的实现
Search Query (HTTP) → Query Embedding
    → Hybrid Search:
        - Milvus Vector Search (semantic)
        - PostgreSQL Full-Text Search (keyword)
        - Neo4j Graph Traversal (related concepts)
    → Result Fusion & Ranking
    → Return to Tool
在这里的过程中我们会调研和使用bm25，然后去验证我们的查询是否正确。
这个步骤比较健壮后，我们会再去进行chat agent的开发。

【已完成 2026-03-24】
- 三级检索架构（Vector + Keyword + Graph）
- RRF（Reciprocal Rank Fusion）融合排序
- PostgreSQL 全文搜索支持
- 混合搜索 API 可用
- 手动测试全部通过
```

- 11 chat agent module
```
这个模块我们将实现基于RAG的chat agent功能。
chat agent功能包括基于图RAG的agent，基于文本RAG的agent等。
我们会使用一些第三方的库来进行chat agent的开发，比如langchain,langgraph等。
User Message (WebSocket) → Django Channels Consumer
    → Query Embedding → Milvus Similarity Search (top_k=5)
    → Neo4j Graph Context Retrieval
    → Context Assembly (retrieved docs + graph info)
    → LLM Prompt Construction → OpenAI API Call
    → Response Streaming → WebSocket → Frontend Display
    → Conversation Storage (PostgreSQL + Milvus)
这里的重点是agent的开发，django websocket的开发，以及整个数据流的实现。
```

- 12 集成测试
```
最后我们来回顾一下整个系统的开发过程，进行一些集成测试，确保整个系统的功能是完整的，并且没有什么大的问题。
我们会编写一些测试用例，来测试整个系统的功能，包括用户管理，文档解析，对象存储，向量数据库操作，关系数据库操作，文本向量化，document pipeline manager，document rag search，chat agent等功能的测试。
然后我们对一些问题进行优化和修改。
```