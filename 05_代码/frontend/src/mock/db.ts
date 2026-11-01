import type {
  AuditLog,
  Dsl,
  Execution,
  LlmCallLog,
  MqttSubscription,
  NodeExecution,
  Role,
  Workflow,
  WorkflowVersion
} from '@/types'

/**
 * Mock 内存库（INF-3）：种子数据与后端 db/init.sql 对齐（2 租户 × 3 角色共 6 用户）。
 * 仅当 VITE_USE_MOCK=true 时生效；数据随页面刷新重置。
 */

export interface MockUser {
  id: number
  tenantId: number
  username: string
  password: string
  displayName: string
  role: Role
  status: string
}

export interface MockTenant {
  id: number
  name: string
  status: string
}

export interface MockQuota {
  tokenTotal: number
  tokenUsed: number
}

export const SAMPLE_ALARM_DSL: Dsl = {
  nodes: [
    { id: 't1', type: 'mqtt-trigger', name: '温度采集', config: {} },
    { id: 'c1', type: 'condition', name: '温度判断(>80)', config: { expression: 'payload.temp > 80' } },
    {
      id: 'h1',
      type: 'http',
      name: '调用告警接口',
      config: {
        url: 'https://api.example.com/alarm',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        bodyTemplate: '{"temp": ${payload.temp}}',
        timeoutMs: 10000
      }
    },
    { id: 'd1', type: 'code', name: '记录正常日志', config: { expression: "'normal: ' + payload.temp" } }
  ],
  edges: [
    { source: 't1', target: 'c1', branch: null },
    { source: 'c1', target: 'h1', branch: 'true' },
    { source: 'c1', target: 'd1', branch: 'false' }
  ]
}

const now = () => new Date().toISOString().slice(0, 19).replace('T', ' ')

export const db = {
  users: [
    { id: 1, tenantId: 1, username: 'admin_acme', password: 'Swa@123456', displayName: 'ACME 管理员', role: 'admin', status: 'active' },
    { id: 2, tenantId: 1, username: 'dev_acme', password: 'Swa@123456', displayName: 'ACME 开发', role: 'dev', status: 'active' },
    { id: 3, tenantId: 1, username: 'viewer_acme', password: 'Swa@123456', displayName: 'ACME 只读', role: 'viewer', status: 'active' },
    { id: 4, tenantId: 2, username: 'admin_globex', password: 'Swa@123456', displayName: 'GLOBEX 管理员', role: 'admin', status: 'active' },
    { id: 5, tenantId: 2, username: 'dev_globex', password: 'Swa@123456', displayName: 'GLOBEX 开发', role: 'dev', status: 'active' },
    { id: 6, tenantId: 2, username: 'viewer_globex', password: 'Swa@123456', displayName: 'GLOBEX 只读', role: 'viewer', status: 'active' }
  ] as MockUser[],
  tenants: [
    { id: 1, name: 'acme', status: 'active' },
    { id: 2, name: 'globex', status: 'active' }
  ] as MockTenant[],
  quotas: new Map<number, MockQuota>([
    [1, { tokenTotal: 1000000, tokenUsed: 1200 }],
    [2, { tokenTotal: 500000, tokenUsed: 0 }]
  ]),
  workflows: [
    { id: 1, name: '设备高温告警流程', description: 'MQTT 温度超阈值触发告警', createdAt: now(), updatedAt: now() }
  ] as Workflow[],
  versions: [
    {
      id: 1,
      workflowId: 1,
      versionNo: 1,
      dslJson: JSON.stringify(SAMPLE_ALARM_DSL),
      status: 'published',
      createdAt: now(),
      updatedAt: now()
    }
  ] as WorkflowVersion[],
  executions: [] as Execution[],
  nodeExecutions: [] as NodeExecution[],
  mqttSubs: [
    { id: 1, topic: 'factory/+/temperature', workflowVersionId: 1, status: 'active', createdAt: now(), updatedAt: now() }
  ] as MqttSubscription[],
  llmCalls: [
    { id: 1, userId: 2, provider: 'deepseek', model: 'deepseek-chat', taskType: 'nl_to_flow', promptTokens: 320, completionTokens: 180, cost: 0.0007, latencyMs: 860, createdAt: now() },
    { id: 2, userId: 2, provider: 'deepseek', model: 'deepseek-chat', taskType: 'agent_reasoning', promptTokens: 512, completionTokens: 300, cost: 0.0011, latencyMs: 1230, createdAt: now() }
  ] as LlmCallLog[],
  auditLogs: [] as AuditLog[],
  /** 幂等键 exec:idem:{user}:{ver}:{reqId} → executionId */
  idempotency: new Map<string, number>(),
  seq: {
    workflow: 1,
    version: 1,
    execution: 0,
    nodeExecution: 0,
    mqttSub: 1,
    llmCall: 2,
    auditLog: 0
  }
}

export function nextId(key: keyof typeof db.seq): number {
  db.seq[key] += 1
  return db.seq[key]
}

export function nowStr(): string {
  return now()
}
