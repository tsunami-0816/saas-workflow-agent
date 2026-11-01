package com.swa.backend.dto;

import jakarta.validation.constraints.NotBlank;

/** 保存流程版本请求：dslJson 为画布 DSL JSON 文本（服务端做 Schema 校验）。 */
public record VersionSaveRequest(@NotBlank String dslJson) {
}
