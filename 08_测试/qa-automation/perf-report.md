# 性能测试报告 · saas-workflow-agent

> 被测接口：`GET /api/v1/workflows?pageNo=1&pageSize=20`（核心读接口，不依赖外部 LLM）
> 环境：本机 Windows，Java 8083（默认 HikariCP 连接池，未显式调参）、MySQL 3310 容器、Redis 6379。
> 工具：Python 多线程轻量压测（`08_测试/qa-automation/perf_test.py`）；**JMeter 未安装，本轮缺双工具交叉验证**（如实标注，见 §4）。

## 1. Python 轻量压测结果（三档并发 × 10s，2026-10-31 重测）

| 并发 | 请求数 | TPS | 平均 RT (ms) | P95 RT (ms) | 错误率 |
|---|---|---|---|---|---|
| 10 | 6,377 | 637.7 | 15.6 | 24.3 | 0.00% |
| 20 | 6,729 | 671.9 | 29.7 | 53.7 | 0.00% |
| 50 | 8,164 | 815.1 | 60.1 | 116.3 | 0.00% |

> 原始数据 `reports/perf_1031.log`；复现命令：`python perf_test.py`（cwd=`08_测试/qa-automation`）。
> 与 10-28 旧值（~1300 TPS）的差异如实标注：本轮同机并存 pytest 全量、8085 服务与浏览器等负载，绝对值不可直接跨日横比，只看同轮趋势。

## 2. 瓶颈分析

1. **TPS 趋势**：并发 10→20→50 时 TPS 637.7→671.9→815.1 **单调上升，50 并发仍未出现饱和拐点**；与 10-28 的「~1300 封顶」结论不同，本轮未观测到吞吐天花板。
2. **RT 与 TPS 关系**：平均 RT 15.6→29.7→60.1ms、P95 24.3→53.7→116.3ms 近似线性增长，说明请求在排队，但排队未压垮吞吐（TPS 仍涨），符合「资源未打满、每请求耗时随并发上升」的特征。
3. **大概率瓶颈候选**：
   - HikariCP 默认 `maximum-pool-size=10`（`application.yml` 未显式配置），10 并发即吃满连接池，20/50 并发在池上排队 —— 对应 RT 近线性增长；
   - MyBatis-Plus 租户拦截器对每条 SQL 追加 `tenant_id`，`workflow` 表若缺 `(tenant_id, deleted)` 索引会放大单查询成本；
   - Tomcat 默认 `max-threads=200`，50 并发未打满，暂不像线程池瓶颈。
4. **外部调用**：本接口仅读 MySQL，无 LLM/MQTT 调用，可排除外部依赖影响。

## 3. 调优建议（具体到配置项）

| 优先级 | 建议 | 预期收益 |
|---|---|---|
| 高 | `spring.datasource.hikari.maximum-pool-size: 20~50`（配合 `minimum-idle`），并观察 MySQL `max_connections` | 提高并发读吞吐，降低排队 RT |
| 高 | 为 `workflow` 建索引 `(tenant_id, deleted, id)`，列表排序/过滤走索引 | 降低单查询成本，抬高 TPS 上限 |
| 中 | 分页 `pageSize` 上限收敛（当前 pageSize=999 也放行），避免大页查询占满连接 | 防止单请求拖垮池 |
| 低 | 若后续引入缓存，可对流程列表做短 TTL 缓存（需评估一致性） | 进一步抬升读吞吐 |

> 结论：本轮 50 并发 TPS 815、P95 116ms、0% 错误率，未观测到饱和拐点；RT 随并发近线性增长，指向连接池/索引成本。对 MVP 演示与中小租户规模够用，调优项列入下版本。

## 4. JMeter 交叉验证（缺失说明）

- 本机 `jmeter` 命令不存在（`Get-Command jmeter` 无结果），**未执行 JMeter 压测**。
- 已交付最小 JMX 脚本 `jmeter/workflow-list.jmx`（线程组 + HTTP 请求 + 聚合报告），安装 JMeter 后可直接：
  `jmeter -n -t jmeter/workflow-list.jmx -l result.jtl`
- 该脚本**未经执行验证**，仅作为交付脚手架；不编造 JMeter 数据。此项作为第 8 步工具覆盖缺口登记，建议下版本补齐。
