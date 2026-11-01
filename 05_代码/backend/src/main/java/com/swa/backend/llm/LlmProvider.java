package com.swa.backend.llm;

import java.util.List;
import java.util.Map;

/**
 * LLM Provider SPI（BE-6.1）：新增厂商 = 新增实现类，不动路由主流程。
 */
public interface LlmProvider {

    /**
     * provider 标识，如 deepseek / openai-mock / claude-mock。
     */
    String name();

    /**
     * 发起对话补全。
     *
     * @param messages OpenAI 风格消息列表 [{role, content}...]
     * @return 统一结果（content + token 用量 + 实际模型名）
     */
    LlmResult chat(List<Map<String, String>> messages);
}
