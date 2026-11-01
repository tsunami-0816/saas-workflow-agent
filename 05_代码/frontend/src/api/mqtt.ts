import request from './request'
import type { MqttSubscription, PageData } from '@/types'

export function pageSubscriptions(params: { pageNo: number; pageSize: number }) {
  return request.get<unknown, PageData<MqttSubscription>>('/mqtt/subscriptions', { params })
}

export function getSubscription(id: number) {
  return request.get<unknown, MqttSubscription>(`/mqtt/subscriptions/${id}`)
}

export function createSubscription(data: { topic: string; workflowVersionId: number; status: string }) {
  return request.post<unknown, MqttSubscription>('/mqtt/subscriptions', data)
}

export function updateSubscription(id: number, data: { topic: string; workflowVersionId: number; status: string }) {
  return request.put<unknown, MqttSubscription>(`/mqtt/subscriptions/${id}`, data)
}

export function deleteSubscription(id: number) {
  return request.delete<unknown, null>(`/mqtt/subscriptions/${id}`)
}
