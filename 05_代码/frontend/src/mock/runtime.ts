import type { Dsl, DslEdge, Execution, NodeExecution } from '@/types'
import { db, nextId, nowStr } from './db'

/**
 * Mock 执行模拟器 + Mock SSE 订阅注册表（INF-3）。
 * 真实模式由 java-backend DAG 引擎 + SseEmitter 提供；此处用定时器模拟
 * 节点按拓扑序逐个 RUNNING→SUCCESS，并通过注册表推送 node/execution 事件。
 */

export interface MockSseHandlers {
  onConnected?: () => void
  onNode?: (node: NodeExecution) => void
  onExecution?: (exec: Execution) => void
}

const listeners = new Map<number, Set<MockSseHandlers>>()
const timers = new Map<number, number[]>()

/** 订阅某执行的实时事件（Mock 版 EventSource） */
export function mockSseSubscribe(executionId: number, handlers: MockSseHandlers): () => void {
  let set = listeners.get(executionId)
  if (!set) {
    set = new Set()
    listeners.set(executionId, set)
  }
  set.add(handlers)
  // 连接建立事件 + 当前快照回放（与真实 SSE 语义一致）
  setTimeout(() => {
    handlers.onConnected?.()
    db.nodeExecutions
      .filter((n) => n.executionId === executionId)
      .forEach((n) => handlers.onNode?.({ ...n }))
    const exec = db.executions.find((e) => e.id === executionId)
    if (exec) handlers.onExecution?.({ ...exec })
  }, 50)
  return () => {
    set.delete(handlers)
  }
}

function emitNode(node: NodeExecution) {
  listeners.get(node.executionId!)?.forEach((h) => h.onNode?.({ ...node }))
}

function emitExecution(exec: Execution) {
  listeners.get(exec.id)?.forEach((h) => h.onExecution?.({ ...exec }))
}

/** 创建 Mock 执行实例并启动模拟推进 */
export function startMockExecution(
  tenantId: number,
  userId: number,
  versionId: number,
  dsl: Dsl,
  triggerType: string,
  triggerPayload: string | null
): Execution {
  const exec: Execution = {
    id: nextId('execution'),
    versionId,
    userId,
    status: 'RUNNING',
    triggerType,
    triggerPayload,
    failReason: null,
    startedAt: nowStr(),
    endedAt: null,
    createdAt: nowStr()
  }
  db.executions.unshift(exec)

  const payloadObj = safeParse(triggerPayload)
  dsl.nodes.forEach((n) => {
    db.nodeExecutions.push({
      id: nextId('nodeExecution'),
      executionId: exec.id,
      nodeId: n.id,
      nodeType: n.type,
      status: 'PENDING',
      inputJson: null,
      outputJson: null,
      retryLog: null,
      errorMessage: null,
      startedAt: null,
      endedAt: null
    })
  })

  runDsl(exec, dsl, payloadObj)
  return exec
}

function safeParse(raw: string | null): Record<string, unknown> {
  if (!raw) return {}
  try {
    return JSON.parse(raw) as Record<string, unknown>
  } catch {
    return {}
  }
}

/** 拓扑推进：每 ~900ms 推进一个节点，直至终态 */
function runDsl(exec: Execution, dsl: Dsl, payload: Record<string, unknown>) {
  const edges = dsl.edges || []
  const bySource = new Map<string, DslEdge[]>()
  edges.forEach((e) => {
    const list = bySource.get(e.source) || []
    list.push(e)
    bySource.set(e.source, list)
  })

  const visited = new Set<string>()
  let currentInput: Record<string, unknown> = { _payload: payload }
  // 起点：入度为 0 的节点（通常为 mqtt-trigger）
  const inDegree = new Map<string, number>()
  dsl.nodes.forEach((n) => inDegree.set(n.id, 0))
  edges.forEach((e) => inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1))
  const queue = dsl.nodes.filter((n) => (inDegree.get(n.id) || 0) === 0).map((n) => n.id)

  const steps: Array<() => void> = []
  while (queue.length > 0) {
    const nodeId = queue.shift()!
    if (visited.has(nodeId)) continue
    visited.add(nodeId)
    const node = dsl.nodes.find((n) => n.id === nodeId)!
    const row = db.nodeExecutions.find((n) => n.executionId === exec.id && n.nodeId === nodeId)!
    const input = currentInput

    steps.push(() => {
      row.status = 'RUNNING'
      row.inputJson = JSON.stringify(input)
      row.startedAt = nowStr()
      emitNode(row)
    })
    steps.push(() => {
      const output = mockNodeOutput(node.type, node.config, input)
      row.status = 'SUCCESS'
      row.outputJson = JSON.stringify(output)
      row.endedAt = nowStr()
      emitNode(row)
      currentInput = output
      // 调度后继：condition 只走求值命中的分支
      const outs = bySource.get(nodeId) || []
      if (node.type === 'condition') {
        const branch = evalCondition(String(node.config?.expression ?? ''), output)
        pickBranch(outs, String(branch)).forEach((t) => queue.push(t))
        row.outputJson = JSON.stringify({ ...output, branch })
        emitNode(row)
      } else {
        outs.forEach((e) => queue.push(e.target))
      }
    })
  }

  // 未访问节点（条件分支未命中）→ SKIPPED
  steps.push(() => {
    db.nodeExecutions
      .filter((n) => n.executionId === exec.id && !visited.has(n.nodeId))
      .forEach((n) => {
        n.status = 'SKIPPED'
        n.endedAt = nowStr()
        emitNode(n)
      })
    exec.status = 'SUCCESS'
    exec.endedAt = nowStr()
    emitExecution(exec)
  })

  const list: number[] = []
  steps.forEach((fn, i) => {
    list.push(window.setTimeout(fn, 400 + i * 900))
  })
  timers.set(exec.id, list)
}

function pickBranch(edges: DslEdge[], branch: string): string[] {
  return edges.filter((e) => e.branch === branch).map((e) => e.target)
}

/** 用 JS 表达式模拟 Aviator 求值（Mock 专用，变量取自输入对象键） */
function evalCondition(expression: string, input: Record<string, unknown>): boolean {
  try {
    const keys = Object.keys(input)
    const fn = new Function(...keys, `return (${expression});`)
    return !!fn(...keys.map((k) => input[k]))
  } catch {
    return true
  }
}

/** 各节点类型的 Mock 输出（贴合后端执行器输出结构） */
function mockNodeOutput(
  type: string,
  config: Record<string, unknown>,
  input: Record<string, unknown>
): Record<string, unknown> {
  switch (type) {
    case 'mqtt-trigger':
      return { payload: (input._payload as Record<string, unknown>) ?? input }
    case 'http':
      return { status: 200, body: { ok: true, url: config.url ?? null }, echoed: input }
    case 'code': {
      let result: unknown = null
      try {
        const keys = Object.keys(input)
        const fn = new Function(...keys, `return (${String(config.expression ?? 'null')});`)
        result = fn(...keys.map((k) => input[k]))
      } catch (e) {
        result = `表达式求值失败: ${String(e)}`
      }
      return { result }
    }
    case 'delay':
      return { delayedMs: config.delayMs ?? 0, ...input }
    case 'agent':
      return {
        status: 'SUCCESS',
        output: { summary: `[Mock] Agent 已完成任务：${String(config.task ?? '').slice(0, 50)}` },
        reasoning: '规划者拆解 → 执行者调用 → 审核者通过（Mock 推理链）'
      }
    default:
      return { ...input }
  }
}
