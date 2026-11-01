package com.swa.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** 创建用户请求（仅 admin）。 */
public record UserCreateRequest(
        @NotBlank @Size(max = 64) String username,
        @NotBlank @Size(min = 8, max = 128) String password,
        @Size(max = 64) String displayName,
        @NotBlank @Pattern(regexp = "admin|dev|viewer") String role) {
}
