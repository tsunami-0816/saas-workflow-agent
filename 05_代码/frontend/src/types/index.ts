/** 与后端接口文档（05_代码/backend/docs/接口文档.md）对齐的类型定义。 */

/** 统一响应壳 */
export interface Result<T = unknown> {
  code: number
  message: string
  data: T
}

/** MyBatis-Plus 分页结构 */
export interface PageData<T> {
  records: T[]
  total: number
  current: number
  size: number
}

export type Role = 'admin' | 'dev' | 'viewer'

export interface LoginResponse {
  token: string
  userId: number
  tenantId: number
  username: string
  role: Role
}

export interface CurrentUser {
  userId: number
  tenantId: number
  username: string
  role: Role
}

export interface Workflow {
  id: number
  name: string
  description: string
  createdAt?: string
  updatedAt?: string
}

export type VersionStatus = 'draft' | 'published' | 'disabled'

export interface WorkflowVersion {
  id: number
  workflowId: number
  versionNo: number
  dslJson: string
  status: VersionStatus
  createdAt?: string
  updatedAt?: string
}

export type ExecutionStatus = 'RUNNING' | 'SUCCESS' | 'FAILED' | 'WAITING'

export interface Execution {
  id: number
  versionId: number
  userId: number
  status: ExecutionStatus
  triggerType: string
  triggerPayload: string | null
  failReason: string | null
  startedAt?: string | null
  endedAt?: string | null
  createdAt?: string
}

export type NodeStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'SKIPPED' | 'WAITING'

export interface NodeExecution {
  id?: number
  executionId?: number
  nodeId: string
  nodeType: string
  status: NodeStatus
  inputJson: string | null
  outputJson: string | null
  retryLog: string | null
  errorMessage: string | null
  startedAt?: string | null
  endedAt?: string | null
}

export interface MqttSubscription {
  id: number
  topic: string
  workflowVersionId: number
  status: string
  createdAt?: string
  updatedAt?: string
}

export interface Quota {
  tenantId: number
  tokenTotal: number
  tokenUsed: number
  remain: number
}

export interface LlmCallLog {
  id: number
  userId: number
  provider: string
  model: string
  taskType: string
  promptTokens: number
  completionTokens: number
  cost: number
  latencyMs: number
  createdAt?: string
}

export interface AuditLog {
  id: number
  userId: number
  action: string
  target: string
  detail: string
  ip: string
  createdAt?: string
}

/* ---------- 流程 DSL（与后端 DslDocument 对齐，禁止携带坐标等额外字段） ---------- */

export type NodeType = 'http' | 'condition' | 'code' | 'delay' | 'agent' | 'mqtt-trigger'

export interface DslNode {
  id: string
  type: NodeType
  name: string
  config: Record<string, unknown>
}

export interface DslEdge {
  source: string
  target: string
  /** 条件分支出边标记 true/false；普通边为 null */
  branch?: string | null
}

export interface Dsl {
  nodes: DslNode[]
  edges: DslEdge[]
}
