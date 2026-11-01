import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { Dsl, Execution, NodeType, Role } from '@/types'
import { db, nextId, nowStr, SAMPLE_ALARM_DSL, type MockUser } from './db'
import { startMockExecution } from './runtime'

/**
 * Mock 适配层（INF-3）：以 axios 自定义 adapter 实现，路由/字段/错误码
 * 与 5A《接口文档.md》一一对应；仅 VITE_USE_MOCK=true 时挂载。
 * 切真实后端：.env 中 VITE_USE_MOCK=false，无需改代码。
 */

interface Ctx {
  user: MockUser
}

interface Route {
  method: string
  pattern: RegExp
  /** roles 为空表示无需登录 */
  roles: Role[]
  handler: (ctx: Ctx | null, match: RegExpMatchArray, query: URLSearchParams, body: any) => unknown
}

const NODE_TYPES: NodeType[] = ['http', 'condition', 'code', 'delay', 'agent', 'mqtt-trigger']

class MockBizError extends Error {
  constructor(
    public code: number,
    message: string,
    public httpStatus = 200
  ) {
    super(message)
  }
}

/** Mock DSL 校验：对齐后端 DslValidator（类型/悬空/入出度/无环） */
function validateDsl(dsl: Dsl) {
  if (!dsl.nodes || dsl.nodes.length === 0) throw new MockError(20006, 'nodes 不能为空')
  const ids = new Set<string>()
  for (const n of dsl.nodes) {
    if (!n.id) throw new MockError(20006, '节点 id 不能为空')
    if (ids.has(n.id)) throw new MockError(20006, `节点 id 重复: ${n.id}`)
    ids.add(n.id)
    if (!NODE_TYPES.includes(n.type)) throw new MockError(20003, `未知节点类型: ${n.type}`)
  }
  const inDeg = new Map<string, number>()
  const outEdges = new Map<string, { target: string; branch?: string | null }[]>()
  dsl.nodes.forEach((n) => {
    inDeg.set(n.id, 0)
    outEdges.set(n.id, [])
  })
  for (const e of dsl.edges || []) {
    if (!ids.has(e.source) || !ids.has(e.target)) throw new MockError(20005, `连线指向不存在的节点: ${e.source}->${e.target}`)
    if (e.source === e.target) throw new MockError(20002, `自环: ${e.source}`)
    inDeg.set(e.target, (inDeg.get(e.target) || 0) + 1)
    outEdges.get(e.source)!.push(e)
  }
  for (const n of dsl.nodes) {
    const inD = inDeg.get(n.id) || 0
    const outs = outEdges.get(n.id) || []
    if (n.type === 'mqtt-trigger' && inD !== 0) throw new MockError(20004, `mqtt-trigger 节点不允许有入边: ${n.id}`)
    if (n.type === 'condition') {
      const branches = new Set(outs.map((o) => o.branch))
      if (outs.length < 1 || !branches.has('true') || !branches.has('false')) {
        throw new MockError(20004, `condition 节点需同时覆盖 true/false 分支: ${n.id}`)
      }
    }
    if (n.type !== 'mqtt-trigger' && inD === 0 && outs.length === 0 && dsl.nodes.length > 1) {
      throw new MockError(20004, `孤立节点: ${n.id}`)
    }
  }
  // Kahn 无环检测
  const remain = new Map(inDeg)
  const queue = [...remain.entries()].filter(([, d]) => d === 0).map(([id]) => id)
  let visited = 0
  while (queue.length) {
    const id = queue.shift()!
    visited++
    for (const e of outEdges.get(id) || []) {
      const d = (remain.get(e.target) || 0) - 1
      remain.set(e.target, d)
      if (d === 0) queue.push(e.target)
    }
  }
  if (visited !== ids.size) throw new MockError(20002, 'DSL 校验失败：存在环形依赖')
}

class MockError extends MockBizError {}

function parseToken(config: InternalAxiosRequestConfig): MockUser | null {
  const header = (config.headers?.Authorization as string) || ''
  const m = /^Bearer mock-token-(\d+)$/.exec(header || '')
  if (!m) return null
  return db.users.find((u) => u.id === Number(m[1])) || null
}

function mustWrite(ctx: Ctx | null): Ctx {
  if (!ctx) throw new MockBizError(10401, '未登录或凭证已失效', 401)
  if (ctx.user.role === 'viewer') throw new MockBizError(10403, '越权访问：角色无权执行该操作', 403)
  return ctx
}

function audit(ctx: Ctx, action: string, target: string, detail: string) {
  db.auditLogs.unshift({
    id: nextId('auditLog'),
    userId: ctx.user.id,
    action,
    target,
    detail,
    ip: '127.0.0.1',
    createdAt: nowStr()
  })
}

function page<T>(list: T[], query: URLSearchParams) {
  const pageNo = Number(query.get('pageNo') || 1)
  const pageSize = Number(query.get('pageSize') || 20)
  const start = (pageNo - 1) * pageSize
  return { records: list.slice(start, start + pageSize), total: list.length, current: pageNo, size: pageSize }
}

function findWorkflow(_ctx: Ctx, id: number) {
  // Mock 简化：租户隔离由真实后端租户拦截器保证，Mock 库默认单租户视角
  const w = db.workflows.find((x) => x.id === id)
  if (!w) throw new MockBizError(20001, '流程不存在')
  return w
}

function findVersion(id: number) {
  const v = db.versions.find((x) => x.id === id)
  if (!v) throw new MockBizError(20007, '流程版本不存在')
  return v
}

const routes: Route[] = [
  {
    method: 'post',
    pattern: /^\/auth\/login$/,
    roles: [],
    handler: (_ctx, _m, _q, body) => {
      const user = db.users.find((u) => u.username === body?.username)
      if (!user || user.password !== body?.password || user.status !== 'active') {
        throw new MockBizError(10401, '账号或密码错误', 401)
      }
      return { token: `mock-token-${user.id}`, userId: user.id, tenantId: user.tenantId, username: user.username, role: user.role }
    }
  },
  {
    method: 'get',
    pattern: /^\/auth\/me$/,
    roles: ['admin', 'dev', 'viewer'],
    handler: (ctx) => ({ userId: ctx!.user.id, tenantId: ctx!.user.tenantId, username: ctx!.user.username, role: ctx!.user.role })
  },
  /* ---------- 流程 ---------- */
  {
    method: 'get',
    pattern: /^\/workflows$/,
    roles: ['admin', 'dev', 'viewer'],
    handler: (ctx, _m, query) => {
      const name = query.get('name')?.trim()
      let list = db.workflows.filter(() => ctx!.user.tenantId > 0)
      if (name) list = list.filter((w) => w.name.includes(name))
      return page([...list].sort((a, b) => b.id - a.id), query)
    }
  },
  {
    method: 'get',
    pattern: /^\/workflows\/(\d+)$/,
    roles: ['admin', 'dev', 'viewer'],
    handler: (ctx, m) => findWorkflow(ctx!, Number(m[1]))
  },
  {
    method: 'post',
    pattern: /^\/workflows$/,
    roles: ['admin', 'dev'],
    handler: (ctx, _m, _q, body) => {
      mustWrite(ctx)
      if (!body?.name) throw new MockBizError(10000, 'name 不能为空')
      const w = { id: nextId('workflow'), name: body.name, description: body.description || '', createdAt: nowStr(), updatedAt: nowStr() }
      db.workflows.push(w)
      audit(ctx!, 'workflow.create', `workflow:${w.id}`, `创建流程 ${w.name}`)
      return w
    }
  },
  {
    method: 'put',
    pattern: /^\/workflows\/(\d+)$/,
    roles: ['admin', 'dev'],
    handler: (ctx, m, _q, body) => {
      const w = findWorkflow(mustWrite(ctx), Number(m[1]))
      w.name = body?.name ?? w.name
      w.description = body?.description ?? w.description
      w.updatedAt = nowStr()
      audit(ctx!, 'workflow.update', `workflow:${w.id}`, `更新流程 ${w.name}`)
      return w
    }
  },
  {
    method: 'delete',
    pattern: /^\/workflows\/(\d+)$/,
    roles: ['admin', 'dev'],
    handler: (ctx, m) => {
      const w = findWorkflow(mustWrite(ctx), Number(m[1]))
      db.workflows = db.workflows.filter((x) => x.id !== w.id)
      audit(ctx!, 'workflow.delete', `workflow:${w.id}`, `删除流程 ${w.name}`)
      return null
    }
  },
  {
    method: 'get',
    pattern: /^\/workflows\/(\d+)\/versions$/,
    roles: ['admin', 'dev', 'viewer'],
    handler: (ctx, m, query) => {
      findWorkflow(ctx!, Number(m[1]))
      const list = db.versions.filter((v) => v.workflowId === Number(m[1])).sort((a, b) => b.versionNo - a.versionNo)
      return page(list, query)
    }
  },
  {
    method: 'post',
    pattern: /^\/workflows\/(\d+)\/versions$/,
    roles: ['admin', 'dev'],
    handler: (ctx, m, _q, body) => {
      const w = findWorkflow(mustWrite(ctx), Number(m[1]))
      let dsl: Dsl
      try {
        dsl = JSON.parse(body?.dslJson || '')
      } catch (e) {
        throw new MockBizError(20006, `JSON 解析失败: ${String(e)}`)
      }
      validateDsl(dsl)
      const maxNo = Math.max(0, ...db.versions.filter((v) => v.workflowId === w.id).map((v) => v.versionNo))
      const v = { id: nextId('version'), workflowId: w.id, versionNo: maxNo + 1, dslJson: body.dslJson, status: 'draft' as const, createdAt: nowStr(), updatedAt: nowStr() }
      db.versions.push(v)
      audit(ctx!, 'workflow.version.save', `workflow:${w.id}`, `保存版本 v${v.versionNo}`)
      return v
    }
  },
  {
    method: 'get',
    pattern: /^\/workflows\/versions\/(\d+)$/,
    roles: ['admin', 'dev', 'viewer'],
    handler: (_ctx, m) => findVersion(Number(m[1]))
  },
  {
    method: 'put',
    pattern: /^\/workflows\/versions\/(\d+)\/publish$/,
    roles: ['admin', 'dev'],
    handler: (ctx, m) => {
      const v = findVersion(Number(m[1]))
      mustWrite(ctx)
      if (v.status !== 'draft') throw new MockBizError(20010, `版本状态流转非法: ${v.status} -> published`)
      v.status = 'published'
      v.updatedAt = nowStr()
      audit(ctx!, 'workflow.version.publish', `version:${v.id}`, `发布版本 v${v.versionNo}`)
      return v
    }
  },
  {
    method: 'put',
    pattern: /^\/workflows\/versions\/(\d+)\/disable$/,
    roles: ['admin', 'dev'],
    handler: (ctx, m) => {
      const v = findVersion(Number(m[1]))
      mustWrite(ctx)
      if (v.status !== 'published') throw new MockBizError(20010, `版本状态流转非法: ${v.status} -> disabled`)
      v.status = 'disabled'
      v.updatedAt = nowStr()
      audit(ctx!, 'workflow.version.disable', `version:${v.id}`, `禁用版本 v${v.versionNo}`)
      return v
    }
  },
  {
    method: 'post',
    pattern: /^\/workflows\/nl-draft$/,
    roles: ['admin', 'dev'],
    handler: (ctx, _m, _q, body) => {
      mustWrite(ctx)
      if (!body?.text || String(body.text).length > 2000) throw new MockBizError(10000, 'text 必填且 ≤2000 字')
      // Mock NL 生成：返回内置「设备高温告警」DSL 草稿
      const w = { id: nextId('workflow'), name: body.workflowName || 'NL 生成流程', description: `由自然语言生成：${String(body.text).slice(0, 80)}`, createdAt: nowStr(), updatedAt: nowStr() }
      db.workflows.push(w)
      const v = { id: nextId('version'), workflowId: w.id, versionNo: 1, dslJson: JSON.stringify(SAMPLE_ALARM_DSL), status: 'draft' as const, createdAt: nowStr(), updatedAt: nowStr() }
      db.versions.push(v)
      audit(ctx!, 'workflow.nl-draft', `workflow:${w.id}`, 'NL 生成草稿')
      return v
    }
  },
  /* ---------- 执行 ---------- */
  {
    method: 'post',
    pattern: /^\/executions$/,
    roles: ['admin', 'dev'],
    handler: (ctx, _m, _q, body) => {
      mustWrite(ctx)
      const v = findVersion(Number(body?.versionId))
      if (v.status === 'disabled') throw new MockBizError(20008, '流程版本已禁用，不可执行')
      if (v.status !== 'published') throw new MockBizError(20009, '仅 published 状态版本可执行')
      if (!body?.clientReqId) throw new MockBizError(10000, 'clientReqId 不能为空')
      const idemKey = `${ctx!.user.id}:${v.id}:${body.clientReqId}`
      const existing = db.idempotency.get(idemKey)
      if (existing) {
        const found = db.executions.find((e) => e.id === existing)
        if (found) return found
        throw new MockBizError(30002, '执行创建失败：幂等占坑冲突，请更换 clientReqId')
      }
      const exec = startMockExecution(ctx!.user.tenantId, ctx!.user.id, v.id, JSON.parse(v.dslJson) as Dsl, 'manual', body.triggerPayload ?? null)
      db.idempotency.set(idemKey, exec.id)
      audit(ctx!, 'execution.create', `execution:${exec.id}`, `触发版本 v${v.versionNo}`)
      return exec
    }
  },
  {
    method: 'get',
    pattern: /^\/executions$/,
    roles: ['admin', 'dev', 'viewer'],
    handler: (ctx, _m, query) => {
      const status = query.get('status')
      let list = db.executions.filter(() => ctx!.user.tenantId > 0)
      if (status) list = list.filter((e) => e.status === status)
      return page([...list], query)
    }
  },
  {
    method: 'get',
    pattern: /^\/executions\/(\d+)$/,
    roles: ['admin', 'dev', 'viewer'],
    handler: (_ctx, m) => {
      const e = db.executions.find((x) => x.id === Number(m[1]))
      if (!e) throw new MockBizError(30001, '执行实例不存在')
      return e
    }
  },
  {
    method: 'get',
    pattern: /^\/executions\/(\d+)\/nodes$/,
    roles: ['admin', 'dev', 'viewer'],
    handler: (_ctx, m) => {
      const id = Number(m[1])
      if (!db.executions.find((x) => x.id === id)) throw new MockBizError(30001, '执行实例不存在')
      return db.nodeExecutions.filter((n) => n.executionId === id).map((n) => ({ ...n }))
    }
  },
  {
    method: 'post',
    pattern: /^\/executions\/(\d+)\/replay$/,
    roles: ['admin', 'dev'],
    handler: (ctx, m) => {
      mustWrite(ctx)
      const src = db.executions.find((x) => x.id === Number(m[1]))
      if (!src) throw new MockBizError(30001, '执行实例不存在')
      const v = findVersion(src.versionId)
      const exec = startMockExecution(ctx!.user.tenantId, ctx!.user.id, v.id, JSON.parse(v.dslJson) as Dsl, 'replay', src.triggerPayload)
      audit(ctx!, 'execution.replay', `execution:${src.id}`, `回放产生新实例 ${exec.id}`)
      return exec
    }
  },
  /* ---------- MQTT 订阅 ---------- */
  {
    method: 'get',
    pattern: /^\/mqtt\/subscriptions$/,
    roles: ['admin', 'dev', 'viewer'],
    handler: (_ctx, _m, query) => page([...db.mqttSubs].sort((a, b) => b.id - a.id), query)
  },
  {
    method: 'get',
    pattern: /^\/mqtt\/subscriptions\/(\d+)$/,
    roles: ['admin', 'dev', 'viewer'],
    handler: (_ctx, m) => {
      const s = db.mqttSubs.find((x) => x.id === Number(m[1]))
      if (!s) throw new MockBizError(50003, 'MQTT 订阅不存在')
      return s
    }
  },
  {
    method: 'post',
    pattern: /^\/mqtt\/subscriptions$/,
    roles: ['admin', 'dev'],
    handler: (ctx, _m, _q, body) => {
      mustWrite(ctx)
      if (!body?.topic) throw new MockBizError(10000, 'topic 不能为空')
      if (db.mqttSubs.some((s) => s.topic === body.topic)) throw new MockBizError(10000, 'topic 已存在')
      findVersion(Number(body.workflowVersionId))
      const s = { id: nextId('mqttSub'), topic: body.topic, workflowVersionId: Number(body.workflowVersionId), status: body.status || 'active', createdAt: nowStr(), updatedAt: nowStr() }
      db.mqttSubs.push(s)
      audit(ctx!, 'mqtt.subscription.create', `mqtt-sub:${s.id}`, `订阅 ${s.topic}`)
      return s
    }
  },
  {
    method: 'put',
    pattern: /^\/mqtt\/subscriptions\/(\d+)$/,
    roles: ['admin', 'dev'],
    handler: (ctx, m, _q, body) => {
      mustWrite(ctx)
      const s = db.mqttSubs.find((x) => x.id === Number(m[1]))
      if (!s) throw new MockBizError(50003, 'MQTT 订阅不存在')
      if (body?.topic && db.mqttSubs.some((x) => x.topic === body.topic && x.id !== s.id)) throw new MockBizError(10000, 'topic 已存在')
      if (body?.workflowVersionId) findVersion(Number(body.workflowVersionId))
      s.topic = body?.topic ?? s.topic
      s.workflowVersionId = Number(body?.workflowVersionId ?? s.workflowVersionId)
      s.status = body?.status ?? s.status
      s.updatedAt = nowStr()
      audit(ctx!, 'mqtt.subscription.update', `mqtt-sub:${s.id}`, `更新订阅 ${s.topic}`)
      return s
    }
  },
  {
    method: 'delete',
    pattern: /^\/mqtt\/subscriptions\/(\d+)$/,
    roles: ['admin', 'dev'],
    handler: (ctx, m) => {
      mustWrite(ctx)
      const s = db.mqttSubs.find((x) => x.id === Number(m[1]))
      if (!s) throw new MockBizError(50003, 'MQTT 订阅不存在')
      db.mqttSubs = db.mqttSubs.filter((x) => x.id !== s.id)
      audit(ctx!, 'mqtt.subscription.delete', `mqtt-sub:${s.id}`, `删除订阅 ${s.topic}`)
      return null
    }
  },
  /* ---------- 额度与台账 ---------- */
  {
    method: 'get',
    pattern: /^\/quota$/,
    roles: ['admin', 'dev', 'viewer'],
    handler: (ctx) => {
      const q = db.quotas.get(ctx!.user.tenantId) || { tokenTotal: 0, tokenUsed: 0 }
      return { tenantId: ctx!.user.tenantId, tokenTotal: q.tokenTotal, tokenUsed: q.tokenUsed, remain: q.tokenTotal - q.tokenUsed }
    }
  },
  {
    method: 'get',
    pattern: /^\/quota\/llm-calls$/,
    roles: ['admin', 'dev', 'viewer'],
    handler: (_ctx, _m, query) => page([...db.llmCalls].sort((a, b) => b.id - a.id), query)
  },
  {
    method: 'get',
    pattern: /^\/quota\/audit-logs$/,
    roles: ['admin'],
    handler: (_ctx, _m, query) => page([...db.auditLogs].sort((a, b) => b.id - a.id), query)
  }
]

/** axios 自定义 adapter：按 method+path 匹配路由，模拟 200ms 网络延迟 */
export const mockAdapter: AxiosAdapter = (config: InternalAxiosRequestConfig) => {
  return new Promise<AxiosResponse>((resolve, reject) => {
    setTimeout(() => {
      try {
        const url = new URL(config.url || '', 'http://mock.local')
        const path = url.pathname.replace(/^\/api\/v1/, '')
        Object.entries((config.params as Record<string, unknown>) || {}).forEach(([k, v]) => {
          if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v))
        })
        const body = typeof config.data === 'string' && config.data ? JSON.parse(config.data) : config.data
        const route = routes.find((r) => r.method === (config.method || 'get').toLowerCase() && r.pattern.test(path))
        if (!route) throw new MockBizError(10004, `Mock 未实现的接口: ${config.method} ${path}`, 404)
        const ctxUser = parseToken(config)
        if (route.roles.length > 0) {
          if (!ctxUser) throw new MockBizError(10401, '未登录或凭证已失效', 401)
          if (!route.roles.includes(ctxUser.role)) throw new MockBizError(10403, '越权访问：角色无权执行该操作', 403)
        }
        const data = route.handler(ctxUser ? { user: ctxUser } : null, path.match(route.pattern)!, url.searchParams, body)
        resolve({
          data: { code: 0, message: 'ok', data },
          status: 200,
          statusText: 'OK',
          headers: {},
          config
        })
      } catch (e) {
        if (e instanceof MockBizError) {
          // 与真实后端一致：401/403/429 走 HTTP 状态码，业务错误 HTTP 200 + 业务码
          resolve({
            data: { code: e.code, message: e.message, data: null },
            status: e.httpStatus,
            statusText: 'BIZ',
            headers: {},
            config
          })
        } else {
          reject(e)
        }
      }
    }, 200)
  })
}
