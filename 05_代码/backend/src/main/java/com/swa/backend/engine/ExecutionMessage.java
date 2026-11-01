package com.swa.backend.engine;

/**
 * 执行调度消息（RabbitMQ JSON 序列化）。
 *
 * @param executionId  执行实例 id
 * @param tenantId     租户 id（Worker 据此恢复 TenantContext，租户拦截器前提）
 * @param resumeNodeId 延时恢复节点 id；null 表示从头调度
 */
public record ExecutionMessage(Long executionId, Long tenantId, String resumeNodeId) {
}
