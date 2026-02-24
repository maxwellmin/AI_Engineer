# Django 配置
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 数据库配置 - 连接到您本地的 PostgreSQL
DB_NAME=MelonMind
DB_USER=maxmelonmind
DB_PASSWORD=melonmind123
DB_HOST=localhost
DB_PORT=5432

# Redis 配置（用于 Celery）
REDIS_URL=redis://localhost:6379/0

# Celery 配置
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Mulves 知识库配置
MULVES_API_KEY=your-mulves-api-key
MULVES_BASE_URL=http://localhost:xxxx
MULVES_TIMEOUT=30

# 日志配置
LOG_LEVEL=INFO

# 其他配置
TIME_ZONE=Asia/Shanghai

# Qwen API 设置
QWEN_API_KEY=xxxxxxx
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
USE_MOCK_EMBEDDING=false

# AI/ML 模型配置
MODEL_LLM_NAME=text-embedding-v4
MODEL_PROVIDER=Aliyun
MODEL_EMBEDDING_NAME=text-embedding-v4
MODEL_TIMEOUT=60
MODEL_MAX_TOKENS=4096
MODEL_TEMPERATURE=0.7

# S3/MinIO 配置
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_REGION_NAME=us-east-1
S3_BUCKET_NAME=melon-documents
S3_USE_SSL=false