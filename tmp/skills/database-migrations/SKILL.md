---
name: database-migrations
description: Database migration best practices for schema changes, data migrations, rollbacks, and zero-downtime deployments across PostgreSQL, MySQL, and common ORMs (Prisma, Drizzle, Django, TypeORM, golang-migrate).
---

# 数据库迁移模式

生产系统安全、可逆的数据库 schema 变更方法。

## 激活时机

- 创建或修改数据库表
- 添加/删除列或索引
- 执行数据迁移（回填、转换）
- 规划零停机 schema 变更
- 为新项目配置迁移工具

## 核心原则

1. **每次变更都是迁移** — 绝不手动修改生产数据库
2. **生产环境迁移只能向前** — 回滚使用新的前向迁移
3. **schema 迁移和数据迁移分离** — 绝不在一个迁移中混合 DDL 和 DML
4. **使用生产级数据量测试迁移** — 在 100 行上成功的迁移可能在 1000 万行时锁表
5. **已部署的迁移不可变** — 绝不编辑已在生产环境运行的迁移

## 迁移安全检查清单

应用任何迁移前：

- [ ] 迁移同时包含 UP 和 DOWN（或明确标记为不可逆）
- [ ] 大表无全表锁（使用并发操作）
- [ ] 新列有默认值或可为空（绝不在无默认值时添加 NOT NULL）
- [ ] 索引并发创建（现有表不使用 CREATE TABLE 内联创建）
- [ ] 数据回填与 schema 变更使用独立迁移
- [ ] 已在生产数据副本上测试
- [ ] 回滚计划已记录

## PostgreSQL 模式

### 安全添加列

```sql
-- 正确：可为空的列，无锁
ALTER TABLE users ADD COLUMN avatar_url TEXT;

-- 正确：带默认值的列（Postgres 11+ 即时完成，无需重写）
ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;

-- 错误：现有表上无默认值的 NOT NULL（需要全表重写）
ALTER TABLE users ADD COLUMN role TEXT NOT NULL;
-- 这会锁表并重写每一行
```

### 无停机添加索引

```sql
-- 错误：大表上阻塞写入
CREATE INDEX idx_users_email ON users (email);

-- 正确：非阻塞，允许并发写入
CREATE INDEX CONCURRENTLY idx_users_email ON users (email);

-- 注意：CONCURRENTLY 不能在事务块内运行
-- 大多数迁移工具需要特殊处理
```

### 重命名列（零停机）

绝不在生产环境直接重命名。使用扩展-收缩模式：

```sql
-- 步骤 1：添加新列（迁移 001）
ALTER TABLE users ADD COLUMN display_name TEXT;

-- 步骤 2：回填数据（迁移 002，数据迁移）
UPDATE users SET display_name = username WHERE display_name IS NULL;

-- 步骤 3：更新应用代码，同时读写两列
-- 部署应用变更

-- 步骤 4：停止写入旧列，删除它（迁移 003）
ALTER TABLE users DROP COLUMN username;
```

### 安全删除列

```sql
-- 步骤 1：移除应用中所有对该列的引用
-- 步骤 2：部署不引用该列的应用版本
-- 步骤 3：在下一个迁移中删除列
ALTER TABLE orders DROP COLUMN legacy_status;

-- Django：使用 SeparateDatabaseAndState 从模型中移除
-- 但不生成 DROP COLUMN（然后在下一个迁移中删除）
```

### 大数据量迁移

```sql
-- 错误：在一个事务中更新所有行（锁表）
UPDATE users SET normalized_email = LOWER(email);

-- 正确：批量更新并显示进度
DO $$
DECLARE
  batch_size INT := 10000;
  rows_updated INT;
BEGIN
  LOOP
    UPDATE users
    SET normalized_email = LOWER(email)
    WHERE id IN (
      SELECT id FROM users
      WHERE normalized_email IS NULL
      LIMIT batch_size
      FOR UPDATE SKIP LOCKED
    );
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    RAISE NOTICE '已更新 % 行', rows_updated;
    EXIT WHEN rows_updated = 0;
    COMMIT;
  END LOOP;
END $$;
```

## Prisma (TypeScript/Node.js)

### 工作流

```bash
# 从 schema 变更创建迁移
npx prisma migrate dev --name add_user_avatar

# 在生产环境应用待执行的迁移
npx prisma migrate deploy

# 重置数据库（仅开发环境）
npx prisma migrate reset

# schema 变更后生成客户端
npx prisma generate
```

### Schema 示例

```prisma
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  avatarUrl String?  @map("avatar_url")
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")
  orders    Order[]

  @@map("users")
  @@index([email])
}
```

### 自定义 SQL 迁移

用于 Prisma 无法表达的操作（并发索引、数据回填）：

```bash
# 创建空迁移，然后手动编辑 SQL
npx prisma migrate dev --create-only --name add_email_index
```

```sql
-- migrations/20240115_add_email_index/migration.sql
-- Prisma 无法生成 CONCURRENTLY，因此手动编写
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users (email);
```

## Drizzle (TypeScript/Node.js)

### 工作流

```bash
# 从 schema 变更生成迁移
npx drizzle-kit generate

# 应用迁移
npx drizzle-kit migrate

# 直接推送 schema（仅开发环境，不生成迁移文件）
npx drizzle-kit push
```

### Schema 示例

```typescript
import { pgTable, text, timestamp, uuid, boolean } from "drizzle-orm/pg-core";

export const users = pgTable("users", {
  id: uuid("id").primaryKey().defaultRandom(),
  email: text("email").notNull().unique(),
  name: text("name"),
  isActive: boolean("is_active").notNull().default(true),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});
```

## Django (Python)

### 工作流

```bash
# 从模型变更生成迁移
python manage.py makemigrations

# 应用迁移
python manage.py migrate

# 显示迁移状态
python manage.py showmigrations

# 生成空迁移用于自定义 SQL
python manage.py makemigrations --empty app_name -n description
```

### 数据迁移

```python
from django.db import migrations

def backfill_display_names(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    batch_size = 5000
    users = User.objects.filter(display_name="")
    while users.exists():
        batch = list(users[:batch_size])
        for user in batch:
            user.display_name = user.username
        User.objects.bulk_update(batch, ["display_name"], batch_size=batch_size)

def reverse_backfill(apps, schema_editor):
    pass  # 数据迁移，无需反向操作

class Migration(migrations.Migration):
    dependencies = [("accounts", "0015_add_display_name")]

    operations = [
        migrations.RunPython(backfill_display_names, reverse_backfill),
    ]
```

### SeparateDatabaseAndState

从 Django 模型中移除列但不立即从数据库删除：

```python
class Migration(migrations.Migration):
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name="user", name="legacy_field"),
            ],
            database_operations=[],  # 暂不操作数据库
        ),
    ]
```

## golang-migrate (Go)

### 工作流

```bash
# 创建迁移文件对
migrate create -ext sql -dir migrations -seq add_user_avatar

# 应用所有待执行的迁移
migrate -path migrations -database "$DATABASE_URL" up

# 回滚最后一个迁移
migrate -path migrations -database "$DATABASE_URL" down 1

# 强制版本（修复脏状态）
migrate -path migrations -database "$DATABASE_URL" force VERSION
```

### 迁移文件

```sql
-- migrations/000003_add_user_avatar.up.sql
ALTER TABLE users ADD COLUMN avatar_url TEXT;
CREATE INDEX CONCURRENTLY idx_users_avatar ON users (avatar_url) WHERE avatar_url IS NOT NULL;

-- migrations/000003_add_user_avatar.down.sql
DROP INDEX IF EXISTS idx_users_avatar;
ALTER TABLE users DROP COLUMN IF EXISTS avatar_url;
```

## 零停机迁移策略

对于关键生产变更，遵循扩展-收缩模式：

```
阶段 1：扩展
  - 添加新列/表（可为空或有默认值）
  - 部署：应用同时写入新旧两处
  - 回填现有数据

阶段 2：迁移
  - 部署：应用从新位置读取，同时写入新旧两处
  - 验证数据一致性

阶段 3：收缩
  - 部署：应用仅使用新位置
  - 在独立迁移中删除旧列/表
```

### 时间线示例

```
第 1 天：迁移添加 new_status 列（可为空）
第 1 天：部署应用 v2 — 同时写入 status 和 new_status
第 2 天：运行回填迁移处理现有行
第 3 天：部署应用 v3 — 仅从 new_status 读取
第 7 天：迁移删除旧 status 列
```

## 反模式

| 反模式 | 失败原因 | 更好的方法 |
|-------------|-------------|-----------------|
| 生产环境手动执行 SQL | 无审计记录，不可重复 | 始终使用迁移文件 |
| 编辑已部署的迁移 | 导致环境间漂移 | 创建新的迁移代替 |
| 无默认值的 NOT NULL | 锁表，重写所有行 | 先添加可为空列，回填，再添加约束 |
| 大表内联索引 | 构建期间阻塞写入 | CREATE INDEX CONCURRENTLY |
| 单个迁移中混合 schema 和数据 | 难以回滚，事务过长 | 分离为独立迁移 |
| 删除代码前先删除列 | 应用因缺少列报错 | 先移除代码，下次部署时删除列 |
