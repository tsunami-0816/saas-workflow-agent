import { executionEventsUrl, getExecutionNodes } from '@/api/execution'
import { mockSseSubscribe } from '@/mock/runtime'
import type { Execution, NodeExecution } from '@/types'
import { TOKEN_KEY, USE_MOCK } from '@/utils/env'

/**
 * 执行事件流客户端（FE-4.2/FE-4.3）。
 * 后端 SSE 仅认 Authorization 头，原生 EventSource 无法自定义请求头，
 * 故真实模式用 fetch 流式解析 text/event-stream；Mock 模式走内存模拟器。
 * 断线重连策略（P2-4）：先拉 /executions/{id}/nodes 快照刷新状态，再指数退避续订。
 */

export interface SseHandlers {
  onNode: (node: NodeExecution) => void
  onExecution: (exec: Partial<Execution> & { id: number }) => void
  onConnected?: () => void
  /** 重连中提示（第几次重试） */
  onReconnecting?: (attempt: number) => void
}

const MAX_RETRY = 8

export class ExecutionEventStream {
  private abort: AbortController | null = null
  private closed = false
  private attempts = 0
  private mockClose: (() => void) | null = null
  private timer: number | null = null

  constructor(
    private executionId: number,
    private handlers: SseHandlers
  ) {}

  start() {
    if (USE_MOCK) {
      this.startMock()
    } else {
      void this.connect()
    }
  }

  close() {
    this.closed = true
    this.abort?.abort()
    this.mockClose?.()
    if (this.timer !== null) window.clearTimeout(this.timer)
  }

  private startMock() {
    this.mockClose = mockSseSubscribe(this.executionId, {
      onConnected: () => this.handlers.onConnected?.(),
      onNode: (n) => this.handlers.onNode(n),
      onExecution: (e) => this.handlers.onExecution(e)
    })
  }

  private async connect() {
    if (this.closed) return
    this.abort = new AbortController()
    try {
      const resp = await fetch(executionEventsUrl(this.executionId), {
        headers: { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) || ''}` },
        signal: this.abort.signal
      })
      if (!resp.ok || !resp.body) {
        throw new Error(`SSE 连接失败 HTTP ${resp.status}`)
      }
      this.attempts = 0
      this.handlers.onConnected?.()
      await this.readLoop(resp.body)
      // 服务端正常关闭（执行结束/超时 30min）：若非主动关闭则按断线处理
      if (!this.closed) await this.reconnect()
    } catch (e) {
      if (this.closed || (e instanceof DOMException && e.name === 'AbortError')) return
      await this.reconnect()
    }
  }

  /** 断线恢复：先拉快照（不丢中间态），再续订（FE-4.3） */
  private async reconnect() {
    if (this.closed) return
    this.attempts += 1
    if (this.attempts > MAX_RETRY) return
    this.handlers.onReconnecting?.(this.attempts)
    try {
      // 快照刷新（失败不阻断续订）
      const nodes = await getExecutionNodes(this.executionId)
      nodes.forEach((n) => this.handlers.onNode(n))
    } catch {
      /* 快照失败仍继续续订，由下一轮重试兜底 */
    }
    const delay = Math.min(1000 * 2 ** (this.attempts - 1), 15000)
    this.timer = window.setTimeout(() => void this.connect(), delay)
  }

  /** 解析 text/event-stream：event: xxx \n data: {...} \n\n */
  private async readLoop(body: ReadableStream<Uint8Array>) {
    const reader = body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let idx: number
      while ((idx = buffer.indexOf('\n\n')) >= 0) {
        const raw = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 2)
        this.dispatch(raw)
      }
    }
  }

  private dispatch(rawEvent: string) {
    let event = 'message'
    const dataLines: string[] = []
    rawEvent.split(/\r?\n/).forEach((line) => {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    })
    const data = dataLines.join('\n')
    if (!data) {
      if (event === 'connected') this.handlers.onConnected?.()
      return
    }
    try {
      const json = JSON.parse(data)
      if (event === 'node') this.handlers.onNode(json as NodeExecution)
      else if (event === 'execution') this.handlers.onExecution(json as Partial<Execution> & { id: number })
      else if (event === 'connected') this.handlers.onConnected?.()
    } catch {
      /* 非 JSON 心跳行忽略 */
    }
  }
}
