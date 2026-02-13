# 本地测试开发环境配置

- 我们的开发测试环境在macos上运行，所以需要安装docker，尽量自己手动操作，以免claude console操作的命令错误，和这些环境冲突。

## Milvus 服务
- MILVUS url: localhost:19530
- attu url: localhost:8080

## celery
- celery url: 待定

## postgresSQL
- url: localhost:5432

## attu 服务启动命令(需要先启动 milvus 服务)
- docker run -d -p 8080:3000 -e MILVUS_URL=172.19.0.4:19530 --name attu zilliz/attu:v2.6

