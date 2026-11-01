import request from './request'
import type { Execution, NodeExecution, PageData } from '@/types'

/** 创建执行（幂等：同 user+version+clientReqId 只建 1 个实例） */
export function createExecution(data: { versionId: number; clientReqId: string; triggerPayload?: string }) {
  return request.post<unknown, Execution>('/executions', data)
}

export function pageExecutions(params: { pageNo: number; pageSize: number; status?: string }) {
  return request.get<unknown, PageData<Execution>>('/executions', { params })
}

export function getExecution(id: number) {
  return request.get<unknown, Execution>(`/executions/${id}`)
}

/** 节点快照（FE-4.3：SSE 断线续订前先拉快照） */
export function getExecutionNodes(id: number) {
  return request.get<unknown, NodeExecution[]>(`/executions/${id}/nodes`)
}

/** 回放：按原参数重新触发，产生新实例 */
export function replayExecution(id: number) {
  return request.post<unknown, Execution>(`/executions/${id}/replay`)
}

/** SSE 事件流地址（fetch 流式订阅，携带 Authorization） */
export function executionEventsUrl(id: number) {
  return `/api/v1/executions/${id}/events`
}
