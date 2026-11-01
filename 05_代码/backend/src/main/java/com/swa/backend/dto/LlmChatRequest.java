package com.swa.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;

import java.util.List;
import java.util.Map;

/** 模型路由统一请求（python-agent / 内部调用）。 */
public record LlmChatRequest(
        @NotBlank @Size(max = 64) String taskType,
        @NotEmpty List<Map<String, String>> messages,
        /** 可选强制指定 provider（默认按 taskType 路由）。 */
        String provider) {
}
