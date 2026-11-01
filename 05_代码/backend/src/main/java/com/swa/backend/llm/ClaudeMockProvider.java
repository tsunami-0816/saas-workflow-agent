package com.swa.backend.llm;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * Claude Mock Provider（BE-6.3）。
 * ⚠️ 协议替身，非真实厂商：不发起外部调用，按 Claude messages 官方响应结构
 * 组装统一结果，token 按字符数/4 估算。用于无真实 key 时跑通路由/计量/额度链路（M4）。
 */
@Component
public class ClaudeMockProvider implements LlmProvider {

    @Override
    public String name() {
        return "claude-mock";
    }

    @Override
    public LlmResult chat(List<Map<String, String>> messages) {
        int promptTokens = OpenAiMockProvider.estimate(messages);
        String content = "[claude-mock 协议替身] 已完成推理，输入消息 " + messages.size() + " 条。";
        return new LlmResult(content, promptTokens, OpenAiMockProvider.estimate(content),
                "claude-3-5-sonnet-mock");
    }
}
