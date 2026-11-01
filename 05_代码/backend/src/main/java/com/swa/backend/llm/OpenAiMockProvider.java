package com.swa.backend.llm;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * OpenAI Mock Provider（BE-6.3）。
 * ⚠️ 协议替身，非真实厂商：不发起外部调用，按 OpenAI chat/completions 官方响应结构
 * 组装统一结果，token 按字符数/4 估算。用于无真实 key 时跑通路由/计量/额度链路（M4）。
 * nl2flow 场景（prompt 含 DSL Schema）返回固定合法 DSL 样例，仅用于打通「生成→校验→存草稿」
 * 链路；它不是语义生成，M5 的真实模型质量仍须配真实 key 后复验（L-04）。
 */
@Component
public class OpenAiMockProvider implements LlmProvider {

    private static final String NL_PROMPT_MARKER = "DSL Schema";

    /** nl2flow 固定样例：MQTT 温度触发 → 超温判断 →（true）HTTP 告警 /（false）记录温度。 */
    private static final String SAMPLE_DSL = """
            {"nodes":[
              {"id":"t1","type":"mqtt-trigger","name":"温度消息","config":{}},
              {"id":"c1","type":"condition","name":"超温判断","config":{"expression":"t1.payload.temp > 80"}},
              {"id":"h1","type":"http","name":"告警通知","config":{"url":"https://example.com/alarm","method":"POST","bodyTemplate":"{\\"temp\\":{{t1.payload.temp}}}","timeoutMs":10000}},
              {"id":"d1","type":"code","name":"记录温度","config":{"expression":"t1.payload.temp"}}
            ],"edges":[
              {"source":"t1","target":"c1"},
              {"source":"c1","target":"h1","branch":"true"},
              {"source":"c1","target":"d1","branch":"false"}
            ]}""";

    @Override
    public String name() {
        return "openai-mock";
    }

    @Override
    public LlmResult chat(List<Map<String, String>> messages) {
        int promptTokens = estimate(messages);
        String content = isNl2FlowPrompt(messages) ? SAMPLE_DSL
                : "[openai-mock 协议替身] 已收到 " + messages.size() + " 条消息，最后一条长度 "
                + lastContentLength(messages) + " 字符。";
        return new LlmResult(content, promptTokens, estimate(content), "gpt-4o-mini-mock");
    }

    static boolean isNl2FlowPrompt(List<Map<String, String>> messages) {
        return messages.stream()
                .anyMatch(m -> String.valueOf(m.get("content")).contains(NL_PROMPT_MARKER));
    }

    static int estimate(List<Map<String, String>> messages) {
        return Math.max(1, messages.stream().mapToInt(m -> String.valueOf(m.get("content")).length()).sum() / 4);
    }

    static int estimate(String content) {
        return Math.max(1, content.length() / 4);
    }

    static int lastContentLength(List<Map<String, String>> messages) {
        if (messages.isEmpty()) {
            return 0;
        }
        return String.valueOf(messages.get(messages.size() - 1).get("content")).length();
    }
}
