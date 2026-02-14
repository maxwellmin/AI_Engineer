---
name: java-coding-standards
description: "Java 编码规范用于 Spring Boot 服务：命名、不可变性、Optional 使用、流、异常、泛型和项目布局。"
---

# Java 编码规范

Spring Boot 服务中可读、可维护的 Java（17+）代码规范。

## 何时激活

- 编写或审查 Spring Boot 项目中的 Java 代码
- 强制命名、不可变性或异常处理约定
- 使用 records、sealed 类或模式匹配（Java 17+）
- 审查 Optional、流或泛型的使用
- 构建包和项目结构

## 核心原则

- 优先清晰而非取巧
- 默认不可变；最小化共享可变状态
- 快速失败并提供有意义的异常
- 一致的命名和包结构

## 命名

```java
// ✅ 类/Record：PascalCase
public class MarketService {}
public record Money(BigDecimal amount, Currency currency) {}

// ✅ 方法/字段：camelCase
private final MarketRepository marketRepository;
public Market findBySlug(String slug) {}

// ✅ 常量：UPPER_SNAKE_CASE
private static final int MAX_PAGE_SIZE = 100;
```

## 不可变性

```java
// ✅ 优先使用 record 和 final 字段
public record MarketDto(Long id, String name, MarketStatus status) {}

public class Market {
  private final Long id;
  private final String name;
  // 只有 getter，没有 setter
}
```

## Optional 使用

```java
// ✅ 从 find* 方法返回 Optional
Optional<Market> market = marketRepository.findBySlug(slug);

// ✅ 使用 map/flatMap 代替 get()
return market
    .map(MarketResponse::from)
    .orElseThrow(() -> new EntityNotFoundException("Market not found"));
```

## 流最佳实践

```java
// ✅ 使用流进行转换，保持管道简短
List<String> names = markets.stream()
    .map(Market::name)
    .filter(Objects::nonNull)
    .toList();

// ❌ 避免复杂的嵌套流；优先使用循环以保持清晰
```

## 异常

- 领域错误使用非受检异常；用上下文包装技术异常
- 创建领域特定异常（如 `MarketNotFoundException`）
- 避免宽泛的 `catch (Exception ex)`，除非重新抛出/集中记录

```java
throw new MarketNotFoundException(slug);
```

## 泛型和类型安全

- 避免原始类型；声明泛型参数
- 可复用工具优先使用有界泛型

```java
public <T extends Identifiable> Map<Long, T> indexById(Collection<T> items) { ... }
```

## 项目结构（Maven/Gradle）

```
src/main/java/com/example/app/
  config/
  controller/
  service/
  repository/
  domain/
  dto/
  util/
src/main/resources/
  application.yml
src/test/java/... （镜像 main）
```

## 格式和风格

- 统一使用 2 或 4 空格（项目标准）
- 每个文件一个公共顶层类型
- 保持方法短小专注；提取辅助方法
- 成员顺序：常量、字段、构造器、公共方法、受保护、私有

## 避免的代码异味

- 长参数列表 → 使用 DTO/builder
- 深层嵌套 → 提前返回
- 魔法数字 → 命名常量
- 静态可变状态 → 优先依赖注入
- 静默 catch 块 → 记录并处理或重新抛出

## 日志

```java
private static final Logger log = LoggerFactory.getLogger(MarketService.class);
log.info("fetch_market slug={}", slug);
log.error("failed_fetch_market slug={}", slug, ex);
```

## 空值处理

- 仅在不可避免时接受 `@Nullable`；否则使用 `@NonNull`
- 在输入上使用 Bean Validation（`@NotNull`、`@NotBlank`）

## 测试期望

- JUnit 5 + AssertJ 用于流畅断言
- Mockito 用于 mock；尽可能避免部分 mock
- 优先确定性测试；无隐藏的 sleep

**记住**：保持代码有意图、有类型、可观测。优先考虑可维护性，除非证明必要，否则不进行微优化。
