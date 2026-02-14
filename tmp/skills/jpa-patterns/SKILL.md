---
name: jpa-patterns
description: JPA/Hibernate 模式，用于实体设计、关系、查询优化、事务、审计、索引、分页和连接池，用于 Spring Boot。
---

# JPA/Hibernate 模式

用于 Spring Boot 中的数据建模、仓库和性能调优。

## 何时激活

- 设计 JPA 实体和表映射
- 定义关系（@OneToMany、@ManyToOne、@ManyToMany）
- 优化查询（N+1 预防、抓取策略、投影）
- 配置事务、审计或软删除
- 设置分页、排序或自定义仓库方法
- 调优连接池（HikariCP）或二级缓存

## 实体设计

```java
@Entity
@Table(name = "markets", indexes = {
  @Index(name = "idx_markets_slug", columnList = "slug", unique = true)
})
@EntityListeners(AuditingEntityListener.class)
public class MarketEntity {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(nullable = false, length = 200)
  private String name;

  @Column(nullable = false, unique = true, length = 120)
  private String slug;

  @Enumerated(EnumType.STRING)
  private MarketStatus status = MarketStatus.ACTIVE;

  @CreatedDate private Instant createdAt;
  @LastModifiedDate private Instant updatedAt;
}
```

启用审计：
```java
@Configuration
@EnableJpaAuditing
class JpaConfig {}
```

## 关系和 N+1 预防

```java
@OneToMany(mappedBy = "market", cascade = CascadeType.ALL, orphanRemoval = true)
private List<PositionEntity> positions = new ArrayList<>();
```

- 默认使用延迟加载；需要时在查询中使用 `JOIN FETCH`
- 集合上避免 `EAGER`；读路径使用 DTO 投影

```java
@Query("select m from MarketEntity m left join fetch m.positions where m.id = :id")
Optional<MarketEntity> findWithPositions(@Param("id") Long id);
```

## 仓库模式

```java
public interface MarketRepository extends JpaRepository<MarketEntity, Long> {
  Optional<MarketEntity> findBySlug(String slug);

  @Query("select m from MarketEntity m where m.status = :status")
  Page<MarketEntity> findByStatus(@Param("status") MarketStatus status, Pageable pageable);
}
```

- 使用投影进行轻量查询：
```java
public interface MarketSummary {
  Long getId();
  String getName();
  MarketStatus getStatus();
}
Page<MarketSummary> findAllBy(Pageable pageable);
```

## 事务

- 用 `@Transactional` 注解服务方法
- 读路径使用 `@Transactional(readOnly = true)` 优化
- 谨慎选择传播行为；避免长事务

```java
@Transactional
public Market updateStatus(Long id, MarketStatus status) {
  MarketEntity entity = repo.findById(id)
      .orElseThrow(() -> new EntityNotFoundException("Market"));
  entity.setStatus(status);
  return Market.from(entity);
}
```

## 分页

```java
PageRequest page = PageRequest.of(pageNumber, pageSize, Sort.by("createdAt").descending());
Page<MarketEntity> markets = repo.findByStatus(MarketStatus.ACTIVE, page);
```

对于游标式分页，在 JPQL 中包含 `id > :lastId` 并排序。

## 索引和性能

- 为常用过滤器添加索引（`status`、`slug`、外键）
- 使用匹配查询模式的复合索引（`status, created_at`）
- 避免 `select *`；只投影需要的列
- 使用 `saveAll` 和 `hibernate.jdbc.batch_size` 批量写入

## 连接池（HikariCP）

推荐配置：
```
spring.datasource.hikari.maximum-pool-size=20
spring.datasource.hikari.minimum-idle=5
spring.datasource.hikari.connection-timeout=30000
spring.datasource.hikari.validation-timeout=5000
```

对于 PostgreSQL LOB 处理，添加：
```
spring.jpa.properties.hibernate.jdbc.lob.non_contextual_creation=true
```

## 缓存

- 一级缓存是每个 EntityManager 的；避免跨事务持有实体
- 对于读密集的实体，谨慎考虑二级缓存；验证驱逐策略

## 迁移

- 使用 Flyway 或 Liquibase；生产环境永远不要依赖 Hibernate 自动 DDL
- 保持迁移幂等和增量；无计划不要删除列

## 测试数据访问

- 优先使用带 Testcontainers 的 `@DataJpaTest` 以模拟生产环境
- 使用日志断言 SQL 效率：设置 `logging.level.org.hibernate.SQL=DEBUG` 和 `logging.level.org.hibernate.orm.jdbc.bind=TRACE` 查看参数值

**记住**：保持实体精简、查询有意图、事务简短。通过抓取策略和投影预防 N+1，并为读写路径建立索引。
