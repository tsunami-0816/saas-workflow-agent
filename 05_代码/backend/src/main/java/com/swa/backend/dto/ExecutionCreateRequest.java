package com.swa.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/** 创建执行请求。clientReqId 为幂等键组成部分，同 user+version+reqId 重发只建 1 个实例。 */
public record ExecutionCreateRequest(
        @NotNull Long versionId,
        @NotBlank @Size(max = 64) String clientReqId,
        /** 触发入参（JSON 文本，可选），作为起点节点输入。 */
        String triggerPayload) {
}
