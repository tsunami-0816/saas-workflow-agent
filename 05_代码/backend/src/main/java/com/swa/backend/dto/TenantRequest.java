package com.swa.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** 租户创建/更新请求（仅 admin）。 */
public record TenantRequest(
        @NotBlank @Size(max = 64) String name,
        @Size(max = 16) String status,
        /** 初始 token 额度（可选）。 */
        Long tokenTotal) {
}
