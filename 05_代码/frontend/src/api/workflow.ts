import request from './request'
import type { PageData, Workflow, WorkflowVersion } from '@/types'

/** 流程分页列表 */
export function pageWorkflows(params: { pageNo: number; pageSize: number; name?: string }) {
  return request.get<unknown, PageData<Workflow>>('/workflows', { params })
}

export function getWorkflow(id: number) {
  return request.get<unknown, Workflow>(`/workflows/${id}`)
}

export function createWorkflow(data: { name: string; description?: string }) {
  return request.post<unknown, Workflow>('/workflows', data)
}

export function updateWorkflow(id: number, data: { name: string; description?: string }) {
  return request.put<unknown, Workflow>(`/workflows/${id}`, data)
}

export function deleteWorkflow(id: number) {
  return request.delete<unknown, null>(`/workflows/${id}`)
}

/** 版本分页 */
export function pageVersions(workflowId: number, params: { pageNo: number; pageSize: number }) {
  return request.get<unknown, PageData<WorkflowVersion>>(`/workflows/${workflowId}/versions`, { params })
}

/** 保存新版本（draft），dslJson 为字符串 */
export function saveVersion(workflowId: number, dslJson: string) {
  return request.post<unknown, WorkflowVersion>(`/workflows/${workflowId}/versions`, { dslJson })
}

export function getVersion(versionId: number) {
  return request.get<unknown, WorkflowVersion>(`/workflows/versions/${versionId}`)
}

export function publishVersion(versionId: number) {
  return request.put<unknown, WorkflowVersion>(`/workflows/versions/${versionId}/publish`)
}

export function disableVersion(versionId: number) {
  return request.put<unknown, WorkflowVersion>(`/workflows/versions/${versionId}/disable`)
}

/** NL→流程草稿：成功返回版本对象（含 dslJson 与 workflowId） */
export function nlDraft(data: { text: string; workflowName?: string }) {
  return request.post<unknown, WorkflowVersion>('/workflows/nl-draft', data)
}
