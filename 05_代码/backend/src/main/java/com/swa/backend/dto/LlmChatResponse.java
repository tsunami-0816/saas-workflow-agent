package com.swa.backend.dto;

/** 模型路由统一响应。 */
public record LlmChatResponse(String content, String provider, String model,
                              int promptTokens, int completionTokens) {
}
