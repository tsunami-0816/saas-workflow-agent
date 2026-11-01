package com.swa.backend.llm;

/**
 * LLM 调用结果（统一结构）。
 */
public record LlmResult(String content, int promptTokens, int completionTokens, String model) {
}
