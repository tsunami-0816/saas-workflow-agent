import request from './request'
import type { AuditLog, LlmCallLog, PageData, Quota } from '@/types'

/** 本租户额度（DB total/used + Redis 实时剩余 remain） */
export function getQuota() {
  return request.get<unknown, Quota>('/quota')
}

/** LLM 调用台账分页 */
export function pageLlmCalls(params: { pageNo: number; pageSize: number }) {
  return request.get<unknown, PageData<LlmCallLog>>('/quota/llm-calls', { params })
}

/** 审计日志分页（仅 admin） */
export function pageAuditLogs(params: { pageNo: number; pageSize: number }) {
  return request.get<unknown, PageData<AuditLog>>('/quota/audit-logs', { params })
}
