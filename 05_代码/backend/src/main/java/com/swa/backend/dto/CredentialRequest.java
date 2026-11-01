package com.swa.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** 连接器凭据创建/更新请求（仅 admin）。configJson 中敏感字段服务端 AES 加密后入库。 */
public record CredentialRequest(
        @NotBlank @Size(max = 64) String connectorType,
        @NotBlank @Size(max = 64) String name,
        @NotBlank String configJson) {
}
