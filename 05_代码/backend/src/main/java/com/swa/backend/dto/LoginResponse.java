package com.swa.backend.dto;

/** 登录响应。 */
public record LoginResponse(String token, Long userId, Long tenantId, String username, String role) {
}
