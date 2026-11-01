package com.swa.backend.dto;

import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** 更新用户请求（仅 admin）；password 为空则不修改。 */
public record UserUpdateRequest(
        @Size(max = 64) String displayName,
        @Pattern(regexp = "admin|dev|viewer") String role,
        @Pattern(regexp = "active|disabled") String status,
        @Size(min = 8, max = 128) String password) {
}
