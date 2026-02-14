# Rule 示例模板

## 说明

Rule 定义了在特定上下文中必须遵循的规则和约束。与 CODEBUDDY.md 中的规则不同，这里是项目级别的自定义规则。

## 文件命名规范

- 使用小写字母和下划线：`database_operations.md`
- 文件名应清晰表达规则的主题

---

# Database Operations Rule

## 适用范围

所有涉及数据库操作的代码，包括：
- Django ORM 查询
- Milvus 向量操作
- Neo4j 图数据库操作
- Redis 缓存操作

## 强制规则

### Django ORM

1. **必须使用 select_related/prefetch_related**

   ```python
   # 错误 - N+1 问题
   documents = Document.objects.all()
   for doc in documents:
       print(doc.user.username)  # 每次循环都查询数据库

   # 正确 - 使用 select_related
   documents = Document.objects.select_related("user").all()
   for doc in documents:
       print(doc.user.username)  # 只查询一次
   ```

2. **必须使用事务处理多表操作**

   ```python
   from django.db import transaction

   with transaction.atomic():
       document = Document.objects.create(...)
       Embedding.objects.create(document=document, ...)
   ```

3. **必须为查询字段添加索引**

   ```python
   class Document(models.Model):
       status = models.CharField(max_length=20, db_index=True)
       created_at = models.DateTimeField(auto_now_add=True, db_index=True)

       class Meta:
           indexes = [
               models.Index(fields=["status", "created_at"]),
           ]
   ```

### Milvus 操作

1. **必须检查 collection 是否存在**

   ```python
   from pymilvus import utility, Collection

   def get_collection(name: str) -> Collection:
       if not utility.has_collection(name):
           raise ValueError(f"Collection {name} does not exist")
       return Collection(name)
   ```

2. **必须在批量操作后调用 flush**

   ```python
   collection.insert(data)
   collection.flush()  # 确保数据持久化
   ```

3. **必须释放 collection 释放内存**

   ```python
   collection = Collection(name)
   collection.load()
   try:
       results = collection.search(...)
   finally:
       collection.release()  # 释放内存
   ```

### Neo4j 操作

1. **必须使用参数化查询防止注入**

   ```python
   # 错误 - Cypher 注入风险
   query = f"MATCH (n:Document {{name: '{name}'}}) RETURN n"

   # 正确 - 参数化查询
   query = "MATCH (n:Document {name: $name}) RETURN n"
   session.run(query, name=name)
   ```

2. **必须使用事务**

   ```python
   with driver.session() as session:
       with session.begin_transaction() as tx:
           tx.run(query, params)
           tx.commit()
   ```

### Redis 操作

1. **必须设置过期时间**

   ```python
   # 错误 - 永不过期
   cache.set("user:123:data", data)

   # 正确 - 设置过期时间
   cache.set("user:123:data", data, timeout=3600)  # 1小时过期
   ```

2. **必须使用原子操作**

   ```python
   from django.core.cache import cache

   # 使用 incr 进行原子递增
   cache.set("counter", 0)
   cache.incr("counter")
   ```

## 性能规则

1. 批量操作优于循环单条操作
2. 使用 only() / defer() 限制查询字段
3. 避免在循环中执行数据库查询
4. 大数据量查询使用分页

## 错误处理

1. 必须捕获数据库连接异常
2. 必须记录数据库操作日志
3. 必须在异常时回滚事务

## 检查清单

- [ ] 是否使用了 select_related/prefetch_related
- [ ] 查询字段是否有索引
- [ ] 是否使用了事务
- [ ] 是否设置了缓存过期时间
- [ ] 是否使用了参数化查询
