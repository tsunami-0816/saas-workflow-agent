package com.swa.backend.dto;

import jakarta.validation.constraints.Size;

/** 流程更新请求。 */
public record WorkflowUpdateRequest(
        @Size(max = 128) String name,
        @Size(max = 512) String description) {
}
