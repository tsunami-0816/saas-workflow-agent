package com.swa.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** 流程创建请求。 */
public record WorkflowCreateRequest(
        @NotBlank @Size(max = 128) String name,
        @Size(max = 512) String description) {
}
