| name | description |
|------|-------------|
| cloud-infrastructure-security | Use this skill when deploying to cloud platforms, configuring infrastructure, managing IAM policies, setting up logging/monitoring, or implementing CI/CD pipelines. Provides cloud security checklist aligned with best practices. |

# 云与基础设施安全技能

本技能确保云基础设施、CI/CD 流水线和部署配置遵循安全最佳实践，并符合行业标准。

## 何时激活

- 部署应用程序到云平台（AWS、Vercel、Railway、Cloudflare）
- 配置 IAM 角色和权限
- 设置 CI/CD 流水线
- 实现基础设施即代码（Terraform、CloudFormation）
- 配置日志和监控
- 在云环境中管理密钥
- 设置 CDN 和边缘安全
- 实现灾难恢复和备份策略

## 云安全检查清单

### 1. IAM 与访问控制

#### 最小权限原则

```yaml
# ✅ 正确：最小权限
iam_role:
  permissions:
    - s3:GetObject  # 仅读取权限
    - s3:ListBucket
  resources:
    - arn:aws:s3:::my-bucket/*  # 仅特定存储桶

# ❌ 错误：权限过宽
iam_role:
  permissions:
    - s3:*  # 所有 S3 操作
  resources:
    - "*"  # 所有资源
```

#### 多因素认证（MFA）

```bash
# 始终为 root/admin 账户启用 MFA
aws iam enable-mfa-device \
  --user-name admin \
  --serial-number arn:aws:iam::123456789:mfa/admin \
  --authentication-code1 123456 \
  --authentication-code2 789012
```

#### 验证步骤

- [ ] 生产环境不使用 root 账户
- [ ] 所有特权账户启用 MFA
- [ ] 服务账户使用角色，而非长期凭证
- [ ] IAM 策略遵循最小权限原则
- [ ] 定期进行访问审查
- [ ] 轮换或删除未使用的凭证

### 2. 密钥管理

#### 云密钥管理器

```typescript
// ✅ 正确：使用云密钥管理器
import { SecretsManager } from '@aws-sdk/client-secrets-manager';

const client = new SecretsManager({ region: 'us-east-1' });
const secret = await client.getSecretValue({ SecretId: 'prod/api-key' });
const apiKey = JSON.parse(secret.SecretString).key;

// ❌ 错误：硬编码或仅使用环境变量
const apiKey = process.env.API_KEY; // 不轮换，不审计
```

#### 密钥轮换

```bash
# 为数据库凭证设置自动轮换
aws secretsmanager rotate-secret \
  --secret-id prod/db-password \
  --rotation-lambda-arn arn:aws:lambda:region:account:function:rotate \
  --rotation-rules AutomaticallyAfterDays=30
```

#### 验证步骤

- [ ] 所有密钥存储在云密钥管理器中（AWS Secrets Manager、Vercel Secrets）
- [ ] 数据库凭证启用自动轮换
- [ ] API 密钥至少每季度轮换一次
- [ ] 代码、日志或错误消息中没有密钥
- [ ] 密钥访问启用审计日志

### 3. 网络安全

#### VPC 和防火墙配置

```terraform
# ✅ 正确：受限安全组
resource "aws_security_group" "app" {
  name = "app-sg"
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]  # 仅内部 VPC
  }
  
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # 仅 HTTPS 出站
  }
}

# ❌ 错误：对互联网开放
resource "aws_security_group" "bad" {
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # 所有端口，所有 IP！
  }
}
```

#### 验证步骤

- [ ] 数据库不可公开访问
- [ ] SSH/RDP 端口仅限于 VPN/堡垒机
- [ ] 安全组遵循最小权限原则
- [ ] 网络 ACL 已配置
- [ ] VPC 流日志已启用

### 4. 日志与监控

#### CloudWatch/日志配置

```typescript
// ✅ 正确：全面的日志记录
import { CloudWatchLogsClient, CreateLogStreamCommand } from '@aws-sdk/client-cloudwatch-logs';

const logSecurityEvent = async (event: SecurityEvent) => {
  await cloudwatch.putLogEvents({
    logGroupName: '/aws/security/events',
    logStreamName: 'authentication',
    logEvents: [{
      timestamp: Date.now(),
      message: JSON.stringify({
        type: event.type,
        userId: event.userId,
        ip: event.ip,
        result: event.result,
        // 永远不记录敏感数据
      })
    }]
  });
};
```

#### 验证步骤

- [ ] 所有服务启用 CloudWatch/日志
- [ ] 记录失败的身份验证尝试
- [ ] 审计管理员操作
- [ ] 配置日志保留期（合规要求 90+ 天）
- [ ] 配置可疑活动告警
- [ ] 日志集中化且防篡改

### 5. CI/CD 流水线安全

#### 安全流水线配置

```yaml
# ✅ 正确：安全的 GitHub Actions 工作流
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read  # 最小权限
      
    steps:
      - uses: actions/checkout@v4
      
      # 扫描密钥
      - name: Secret scanning
        uses: trufflesecurity/trufflehog@main
        
      # 依赖审计
      - name: Audit dependencies
        run: npm audit --audit-level=high
        
      # 使用 OIDC，而非长期令牌
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789:role/GitHubActionsRole
          aws-region: us-east-1
```

#### 供应链安全

```json
// package.json - 使用锁文件和完整性检查
{
  "scripts": {
    "install": "npm ci",  // 使用 ci 进行可重现构建
    "audit": "npm audit --audit-level=moderate",
    "check": "npm outdated"
  }
}
```

#### 验证步骤

- [ ] 使用 OIDC 而非长期凭证
- [ ] 流水线中进行密钥扫描
- [ ] 依赖漏洞扫描
- [ ] 容器镜像扫描（如适用）
- [ ] 强制执行分支保护规则
- [ ] 合并前需要代码审查
- [ ] 强制签名提交

### 6. Cloudflare 与 CDN 安全

#### Cloudflare 安全配置

```typescript
// ✅ 正确：带有安全头的 Cloudflare Workers
export default {
  async fetch(request: Request): Promise<Response> {
    const response = await fetch(request);
    
    // 添加安全头
    const headers = new Headers(response.headers);
    headers.set('X-Frame-Options', 'DENY');
    headers.set('X-Content-Type-Options', 'nosniff');
    headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
    headers.set('Permissions-Policy', 'geolocation=(), microphone=()');
    
    return new Response(response.body, {
      status: response.status,
      headers
    });
  }
};
```

#### WAF 规则

```bash
# 启用 Cloudflare WAF 托管规则
# - OWASP 核心规则集
# - Cloudflare 托管规则集
# - 速率限制规则
# - 机器人保护
```

#### 验证步骤

- [ ] 启用带有 OWASP 规则的 WAF
- [ ] 配置速率限制
- [ ] 激活机器人保护
- [ ] 启用 DDoS 保护
- [ ] 配置安全头
- [ ] 启用 SSL/TLS 严格模式

### 7. 备份与灾难恢复

#### 自动备份

```terraform
# ✅ 正确：自动 RDS 备份
resource "aws_db_instance" "main" {
  allocated_storage     = 20
  engine               = "postgres"
  
  backup_retention_period = 30  # 30 天保留
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  enabled_cloudwatch_logs_exports = ["postgresql"]
  
  deletion_protection = true  # 防止意外删除
}
```

#### 验证步骤

- [ ] 配置自动每日备份
- [ ] 备份保留期符合合规要求
- [ ] 启用时间点恢复
- [ ] 每季度进行备份测试
- [ ] 灾难恢复计划已文档化
- [ ] RPO 和 RTO 已定义并测试

## 部署前云安全检查清单

在任何生产云部署之前：

- [ ] **IAM**：不使用 root 账户，启用 MFA，最小权限策略
- [ ] **密钥**：所有密钥在云密钥管理器中并启用轮换
- [ ] **网络**：安全组受限，数据库不公开
- [ ] **日志**：启用 CloudWatch/日志并设置保留期
- [ ] **监控**：配置异常告警
- [ ] **CI/CD**：OIDC 认证，密钥扫描，依赖审计
- [ ] **CDN/WAF**：启用 Cloudflare WAF 和 OWASP 规则
- [ ] **加密**：数据静态和传输加密
- [ ] **备份**：自动备份并测试恢复
- [ ] **合规**：满足 GDPR/HIPAA 要求（如适用）
- [ ] **文档**：基础设施已文档化，运维手册已创建
- [ ] **事件响应**：安全事件计划已就位

## 常见云安全错误配置

### S3 存储桶暴露

```bash
# ❌ 错误：公开存储桶
aws s3api put-bucket-acl --bucket my-bucket --acl public-read

# ✅ 正确：私有存储桶并设置特定访问
aws s3api put-bucket-acl --bucket my-bucket --acl private
aws s3api put-bucket-policy --bucket my-bucket --policy file://policy.json
```

### RDS 公开访问

```terraform
# ❌ 错误
resource "aws_db_instance" "bad" {
  publicly_accessible = true  # 永远不要这样做！
}

# ✅ 正确
resource "aws_db_instance" "good" {
  publicly_accessible = false
  vpc_security_group_ids = [aws_security_group.db.id]
}
```

## 资源

- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
- [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
- [Cloudflare Security Documentation](https://developers.cloudflare.com/security/)
- [OWASP Cloud Security](https://owasp.org/www-project-cloud-security/)
- [Terraform Security Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/)

**记住**：云错误配置是数据泄露的主要原因。一个暴露的 S3 存储桶或权限过宽的 IAM 策略就可能危及整个基础设施。始终遵循最小权限原则和纵深防御策略。
