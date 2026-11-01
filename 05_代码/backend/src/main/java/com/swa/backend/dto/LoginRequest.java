package com.swa.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** 登录请求。 */
public record LoginRequest(
        @NotBlank @Size(max = 64) String username,
        @NotBlank @Size(max = 128) String password,
        /** 前端传也无效果：tenantId 一律以登录用户/token 为准。 */
        Long tenantId) {
}
