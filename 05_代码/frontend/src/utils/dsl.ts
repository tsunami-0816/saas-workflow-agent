import type { Graph, Node } from '@antv/x6'
import type { Dsl, DslNode, NodeType } from '@/types'

/**
 * DSL 序列化/反序列化（FE-2.3）：
 * - 导出结构严格对齐后端 DslDocument：nodes(id/type/name/config) + edges(source/target/branch)，
 *   不携带坐标等额外字段（坐标仅存 localStorage 提升体验，不进 DSL）。
 * - 入出度/类型/无环的最终判据以后端 DslValidator 为准，前端保存前做同口径预检。
 */

export const NODE_TYPE_META: Record<NodeType, { label: string; color: string; desc: string }> = {
  'mqtt-trigger': { label: 'MQTT 触发', color: '#8e44ad', desc: '订阅 topic 消息触发流程（入度须为 0）' },
  http: { label: 'HTTP API', color: '#2f80ed', desc: '调用外部 HTTP 接口' },
  condition: { label: '条件分支', color: '#e67e22', desc: 'Aviator 表达式求值，出边标记 true/false' },
  agent: { label: 'Agent 任务', color: '#27ae60', desc: '调用 python-agent 三角色编排' },
  code: { label: '代码块', color: '#16a085', desc: 'Aviator 沙箱表达式求值' },
  delay: { label: '延时', color: '#7f8c8d', desc: 'TTL+DLX 延时后继续调度' }
}

export interface NodeData {
  type: NodeType
  name: string
  config: Record<string, unknown>
  [key: string]: unknown
}

/** 画布 → DSL 文本 */
export function graphToDsl(graph: Graph): string {
  const nodes: DslNode[] = graph.getNodes().map((n) => {
    const data = (n.getData() || {}) as NodeData
    return { id: n.id, type: data.type, name: data.name, config: data.config || {} }
  })
  const edges = graph.getEdges().map((e) => {
    const data = (e.getData() || {}) as { branch?: string | null }
    return {
      source: e.getSourceCellId(),
      target: e.getTargetCellId(),
      branch: data.branch ?? null
    }
  })
  return JSON.stringify({ nodes, edges })
}

/** DSL → X6 fromJSON 结构；positions 可选（localStorage 缓存的坐标），缺省自动分层布局 */
export function dslToGraphData(
  dsl: Dsl,
  positions?: Record<string, { x: number; y: number }>
): { nodes: Node.Metadata[]; edges: object[] } {
  const layout = positions || autoLayout(dsl)
  const nodes: Node.Metadata[] = dsl.nodes.map((n) => ({
    id: n.id,
    shape: 'rect',
    x: layout[n.id]?.x ?? 80,
    y: layout[n.id]?.y ?? 80,
    width: 160,
    height: 56,
    label: n.name,
    attrs: nodeAttrs(NODE_TYPE_META[n.type]?.color || '#666'),
    ports: portGroups(),
    data: { type: n.type, name: n.name, config: n.config || {} } satisfies NodeData
  }))
  const edges = (dsl.edges || []).map((e) => ({
    source: { cell: e.source, port: 'out' },
    target: { cell: e.target, port: 'in' },
    attrs: { line: { stroke: '#a2b1c3', strokeWidth: 1.5, targetMarker: { name: 'block', size: 8 } } },
    labels: e.branch ? [{ attrs: { label: { text: e.branch, fill: e.branch === 'true' ? '#27ae60' : '#c0392b' } } }] : [],
    data: { branch: e.branch ?? null }
  }))
  return { nodes, edges }
}

/** 简单分层布局：按 BFS 深度分层横排 */
export function autoLayout(dsl: Dsl): Record<string, { x: number; y: number }> {
  const inDeg = new Map<string, number>()
  const outs = new Map<string, string[]>()
  dsl.nodes.forEach((n) => {
    inDeg.set(n.id, 0)
    outs.set(n.id, [])
  })
  ;(dsl.edges || []).forEach((e) => {
    inDeg.set(e.target, (inDeg.get(e.target) || 0) + 1)
    outs.get(e.source)?.push(e.target)
  })
  const depth = new Map<string, number>()
  const queue: string[] = []
  dsl.nodes.forEach((n) => {
    if ((inDeg.get(n.id) || 0) === 0) {
      queue.push(n.id)
      depth.set(n.id, 0)
    }
  })
  while (queue.length) {
    const id = queue.shift()!
    const d = depth.get(id) || 0
    ;(outs.get(id) || []).forEach((t) => {
      if ((depth.get(t) ?? -1) < d + 1) depth.set(t, d + 1)
      queue.push(t)
    })
  }
  const levels = new Map<number, string[]>()
  dsl.nodes.forEach((n) => {
    const d = depth.get(n.id) ?? 0
    const arr = levels.get(d) || []
    arr.push(n.id)
    levels.set(d, arr)
  })
  const pos: Record<string, { x: number; y: number }> = {}
  levels.forEach((ids, d) => {
    ids.forEach((id, i) => {
      pos[id] = { x: 80 + i * 220, y: 60 + d * 120 }
    })
  })
  return pos
}

export function nodeAttrs(color: string) {
  return {
    body: { fill: '#fff', stroke: color, strokeWidth: 2, rx: 6, ry: 6 },
    label: { fill: '#1f2d3d', fontSize: 13 }
  }
}

export function portGroups() {
  const circle = {
    attrs: {
      circle: { r: 5, magnet: true, stroke: '#5f95ff', fill: '#fff', strokeWidth: 1.5 }
    }
  }
  return {
    groups: {
      in: { position: 'top', attrs: circle.attrs },
      out: { position: 'bottom', attrs: circle.attrs }
    },
    items: [
      { id: 'in', group: 'in' },
      { id: 'out', group: 'out' }
    ]
  }
}

/** 保存前预检（口径同后端 DslValidator；最终以服务端为准） */
export function precheckDsl(dsl: Dsl): string | null {
  if (!dsl.nodes.length) return '画布为空，请先拖入节点'
  const ids = new Set(dsl.nodes.map((n) => n.id))
  for (const e of dsl.edges) {
    if (!ids.has(e.source) || !ids.has(e.target)) return `连线指向不存在的节点: ${e.source} -> ${e.target}`
  }
  const inDeg = new Map<string, number>()
  const outEdges = new Map<string, { target: string; branch?: string | null }[]>()
  dsl.nodes.forEach((n) => {
    inDeg.set(n.id, 0)
    outEdges.set(n.id, [])
  })
  dsl.edges.forEach((e) => {
    inDeg.set(e.target, (inDeg.get(e.target) || 0) + 1)
    outEdges.get(e.source)!.push(e)
  })
  for (const n of dsl.nodes) {
    const outs = outEdges.get(n.id) || []
    if (n.type === 'mqtt-trigger' && (inDeg.get(n.id) || 0) !== 0) return `「${n.name}」MQTT 触发节点不允许有入边`
    if (n.type === 'condition') {
      const branches = new Set(outs.map((o) => o.branch))
      if (!branches.has('true') || !branches.has('false')) return `「${n.name}」条件分支需同时覆盖 true/false 两条出边`
    }
    if (n.type !== 'mqtt-trigger' && (inDeg.get(n.id) || 0) === 0 && outs.length === 0 && dsl.nodes.length > 1) {
      return `「${n.name}」是孤立节点，请连线或删除`
    }
    if (!n.name?.trim()) return '存在未命名节点'
  }
  // 无环检测（Kahn）
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
  if (visited !== ids.size) return '流程存在环形依赖，请调整连线'
  return null
}

/** 节点配置必填/格式校验（FE-2.2，保存时全量复核；表单层即时拦截在 node-config-panel） */
export function validateNodeConfig(type: NodeType, config: Record<string, unknown>): string | null {
  switch (type) {
    case 'http': {
      const url = String(config.url ?? '')
      if (!url) return 'HTTP 节点缺少 config.url'
      if (!/^https?:\/\/.+/.test(url)) return `HTTP 节点 url 格式非法: ${url}`
      if (url.length > 512) return 'HTTP 节点 url 超长（>512）'
      if (config.timeoutMs !== undefined) {
        const t = Number(config.timeoutMs)
        if (!Number.isFinite(t) || t < 100 || t > 120000) return 'HTTP 节点 timeoutMs 须在 [100, 120000] 毫秒'
      }
      return null
    }
    case 'condition':
    case 'code': {
      const expr = String(config.expression ?? '')
      if (!expr.trim()) return `${type === 'condition' ? '条件分支' : '代码块'}节点缺少 config.expression`
      if (expr.length > 512) return 'expression 超长（>512）'
      return null
    }
    case 'delay': {
      const d = Number(config.delayMs)
      if (!Number.isFinite(d) || d <= 0 || d > 86400000) return '延时节点 delayMs 须在 (0, 86400000] 毫秒'
      return null
    }
    case 'agent': {
      const task = String(config.task ?? '')
      if (!task.trim()) return 'Agent 节点缺少 config.task'
      if (task.length > 1000) return 'Agent 任务描述超长（>1000）'
      return null
    }
    case 'mqtt-trigger':
      return null
    default:
      return null
  }
}

/** 生成节点 id：类型前缀 + 序号（可读、稳定，便于 DSL 审查） */
export function genNodeId(type: NodeType, graph: Graph): string {
  const prefix = { 'mqtt-trigger': 't', http: 'h', condition: 'c', agent: 'a', code: 's', delay: 'd' }[type]
  let i = 1
  const existing = new Set(graph.getNodes().map((n) => n.id))
  while (existing.has(`${prefix}${i}`)) i++
  return `${prefix}${i}`
}
