package com.swa.backend.llm;

import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * DeepSeek Provider（BE-6.2）：真实调用，兼容 OpenAI chat/completions 协议。
 * key 走环境变量 DEEPSEEK_API_KEY，日志禁止打印。
 */
@Component
public class DeepSeekProvider implements LlmProvider {

    private final RestTemplate restTemplate;
    private final String baseUrl;
    private final String apiKey;

    public DeepSeekProvider(@Value("${llm.deepseek.base-url}") String baseUrl,
                            @Value("${llm.deepseek.api-key:}") String apiKey) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(60_000);
        this.restTemplate = new RestTemplate(factory);
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
    }

    @Override
    public String name() {
        return "deepseek";
    }

    @Override
    public LlmResult chat(List<Map<String, String>> messages) {
        if (apiKey == null || apiKey.isBlank()) {
            throw new BizException(ErrorCode.LLM_CALL_FAILED, "DEEPSEEK_API_KEY 未配置");
        }
        Map<String, Object> body = new HashMap<>();
        body.put("model", "deepseek-chat");
        body.put("messages", messages);
        body.put("stream", false);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setBearerAuth(apiKey);
        try {
            Map<?, ?> response = restTemplate.postForObject(baseUrl + "/chat/completions",
                    new HttpEntity<>(body, headers), Map.class);
            return parse(response);
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            throw new BizException(ErrorCode.LLM_CALL_FAILED, "deepseek 调用失败: " + e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    private LlmResult parse(Map<?, ?> response) {
        if (response == null) {
            throw new BizException(ErrorCode.LLM_CALL_FAILED, "deepseek 响应为空");
        }
        List<Map<String, Object>> choices = (List<Map<String, Object>>) response.get("choices");
        if (choices == null || choices.isEmpty()) {
            throw new BizException(ErrorCode.LLM_CALL_FAILED, "deepseek 响应无 choices");
        }
        Map<String, Object> message = (Map<String, Object>) choices.get(0).get("message");
        String content = message == null ? "" : String.valueOf(message.get("content"));
        Map<String, Object> usage = (Map<String, Object>) response.get("usage");
        int promptTokens = usageNumber(usage, "prompt_tokens");
        int completionTokens = usageNumber(usage, "completion_tokens");
        Object modelRaw = response.get("model");
        String model = modelRaw == null ? "deepseek-chat" : String.valueOf(modelRaw);
        return new LlmResult(content, promptTokens, completionTokens, model);
    }

    private static int usageNumber(Map<String, Object> usage, String key) {
        if (usage == null || !(usage.get(key) instanceof Number n)) {
            return 0;
        }
        return n.intValue();
    }
}
