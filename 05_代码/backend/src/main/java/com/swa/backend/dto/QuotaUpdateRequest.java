package com.swa.backend.dto;

import jakarta.validation.constraints.NotNull;

/** 租户额度配置请求（仅 admin）。 */
public record QuotaUpdateRequest(@NotNull Long tokenTotal) {
}
