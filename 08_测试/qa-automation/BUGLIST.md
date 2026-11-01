# BUGLIST · saas-workflow-agent 第 8 步全量测试

> 测试范围：认证/流程 CRUD/DSL 校验/版本状态机/执行与幂等/节点快照/重放/额度与台账/MQTT 订阅/租户隔离/角色权限 + L3 落库 + L4 主链路/M2/M3/M6。
> 结论：**P0 = 0，P1 = 0**；P2/P3 各若干，按规则本轮不修，移交第 10 步下版本规划。

## 一、P0 / P1（本轮必修）

无。首轮 10 条 failed 经逐条定位均为**测试脚本自身缺陷**（`_dsl` 参数展平、响应字段按 `execId` 断言），非产品缺陷，修正脚本后全部转绿，详见《第一轮全量测试报告》。

## 二、P2 / P3（待优化，本轮不修）

### BUG-001 · P2 · 创建流程响应体 tenantId 未回填

- **复现步骤**：`POST /api/v1/workflows`，body `{"name":"QA-创建-正向-001"}`，携带 dev_acme token。
- **预期结果**：响应 `data.tenantId = 1`（与列表/详情接口一致）。
- **实际结果**：响应 `data.tenantId = null`；随后 `GET /api/v1/workflows/{id}` 返回 `tenantId=1`。
- **根因定位**：
  - [WorkflowService.java:51-57](file:///d:/lg/project/工作流测试/projects/saas-workflow-agent/05_代码/backend/src/main/java/com/swa/backend/service/WorkflowService.java#L51-L57) 只 `setName/setDescription` 后 `insert`，未给实体 `setTenantId`。
  - [MybatisPlusConfig.java:29-53](file:///d:/lg/project/工作流测试/projects/saas-workflow-agent/05_代码/backend/src/main/java/com/swa/backend/config/MybatisPlusConfig.java#L29-L53) 的 `TenantLineInnerInterceptor` 只把 `tenant_id` 注入 SQL，**不会回填实体对象**；因此库里有值、响应对象里为 null。
  - 对照 [ExecutionService.java:125](file:///d:/lg/project/工作流测试/projects/saas-workflow-agent/05_代码/backend/src/main/java/com/swa/backend/service/ExecutionService.java#L125) 显式 `execution.setTenantId(tenantId)`，执行接口响应正常。
- **修复建议**：`createWorkflow` 内 `workflow.setTenantId(TenantContext.getTenantId())` 后再 insert（一处一行）。
- **状态**：open（P2，下版本修）

### BUG-002 · P3 · 接口文档与实现的状态机口径不一致（disabled → published）

- **复现步骤**：版本先 `publish` 再 `disable`，随后再次 `PUT /versions/{id}/publish`。
- **预期结果（按接口文档 §4.2）**：文档写「发布（draft→published）」，未提禁用后回切。
- **实际结果**：返回 code=0，版本重新变为 published。
- **根因定位**：[WorkflowService.java:112-126](file:///d:/lg/project/工作流测试/projects/saas-workflow-agent/05_代码/backend/src/main/java/com/swa/backend/service/WorkflowService.java#L112-L126) 注释与代码明确允许 `draft/disabled → published`（disabled 作为灰度回切锚点），属**实现有意为之**，文档漏写。
- **修复建议**：接口文档 §4.2 补一句「disabled 可重新发布，用于灰度回切」。
- **状态**：open（P3 文档修订，下版本）

### BUG-003 · P3 · 创建/重放执行响应字段缺少文档示例

- **复现步骤**：`POST /api/v1/executions` 成功后读取响应 `data`。
- **预期结果**：接口文档给出创建/重放响应字段示例。
- **实际结果**：文档 §5 只描述执行对象状态，未给创建/重放响应示例；实际返回实体字段为 `id`（不是 `execId`）。
- **根因定位**：[ExecutionController.java:49-52](file:///d:/lg/project/工作流测试/projects/saas-workflow-agent/05_代码/backend/src/main/java/com/swa/backend/controller/ExecutionController.java#L49-L52) 与 [ExecutionController.java:89-92](file:///d:/lg/project/工作流测试/projects/saas-workflow-agent/05_代码/backend/src/main/java/com/swa/backend/controller/ExecutionController.java#L89-L92) 返回 `Result<Execution>`，实体主键字段名 `id`。
- **修复建议**：接口文档 §5 补创建/重放响应示例（`id/tenantId/versionId/status/...`），并注明与列表/详情同构。
- **状态**：open（P3 文档修订，下版本）

## 三、未覆盖场景（本轮不覆盖，登记移交）

- 前端画布 UI 交互（拖拽/连线/撤销）→ 第 9 步人工走查。
- NL→流程 20 条人工评审（M5）→ 无真实 LLM key，见《基线指标验证表》M5。
- SSE 断线重连、执行卡死 sweeper 收敛的长稳场景 → 下版本专项。
- 50+ 并发写执行（M2 只验证 100 实例创建与隔离，未压写吞吐上限）→ 下版本容量测试。
