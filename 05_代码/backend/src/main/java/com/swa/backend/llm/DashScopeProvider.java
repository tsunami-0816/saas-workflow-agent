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
 * DashScope（通义千问）Provider：OpenAI 兼容协议。
 * base-url 指向 DashScope 专属实例的 compatible-mode/v1，model 从配置注入（qwen-plus 等）。
 * key 走环境变量 DASHSCOPE_API_KEY，日志禁止打印。
 */
@Component
public class DashScopeProvider implements LlmProvider {

    private final RestTemplate restTemplate;
    private final String baseUrl;
    private final String apiKey;
    private final String model;

    public DashScopeProvider(@Value("${llm.dashscope.base-url}") String baseUrl,
                             @Value("${llm.dashscope.api-key:}") String apiKey,
                             @Value("${llm.dashscope.model:qwen-plus}") String model) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(60_000);
        this.restTemplate = new RestTemplate(factory);
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.model = model;
    }

    @Override
    public String name() {
        return "dashscope";
    }

    @Override
    public LlmResult chat(List<Map<String, String>> messages) {
        if (apiKey == null || apiKey.isBlank()) {
            throw new BizException(ErrorCode.LLM_CALL_FAILED, "DASHSCOPE_API_KEY 未配置");
        }
        Map<String, Object> body = new HashMap<>();
        body.put("model", model);
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
            throw new BizException(ErrorCode.LLM_CALL_FAILED, "dashscope 调用失败: " + e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    private LlmResult parse(Map<?, ?> response) {
        if (response == null) {
            throw new BizException(ErrorCode.LLM_CALL_FAILED, "dashscope 响应为空");
        }
        List<Map<String, Object>> choices = (List<Map<String, Object>>) response.get("choices");
        if (choices == null || choices.isEmpty()) {
            throw new BizException(ErrorCode.LLM_CALL_FAILED, "dashscope 响应无 choices");
        }
        Map<String, Object> message = (Map<String, Object>) choices.get(0).get("message");
        String content = message == null ? "" : String.valueOf(message.get("content"));
        Map<String, Object> usage = (Map<String, Object>) response.get("usage");
        int promptTokens = usageNumber(usage, "prompt_tokens");
        int completionTokens = usageNumber(usage, "completion_tokens");
        Object modelRaw = response.get("model");
        String actualModel = modelRaw == null ? model : String.valueOf(modelRaw);
        return new LlmResult(content, promptTokens, completionTokens, actualModel);
    }

    private static int usageNumber(Map<String, Object> usage, String key) {
        if (usage == null || !(usage.get(key) instanceof Number n)) {
            return 0;
        }
        return n.intValue();
    }
}
