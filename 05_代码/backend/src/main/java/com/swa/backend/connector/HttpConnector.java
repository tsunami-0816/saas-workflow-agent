package com.swa.backend.connector;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.entity.ConnectorCredential;
import com.swa.backend.mapper.ConnectorCredentialMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * HTTP 连接器（BE-7.1 首个实现）。
 * config: url / method(默认 GET) / headers / bodyTemplate / timeoutMs(默认 10000) / credentialId(可选)。
 * 模板变量 {{var}} 从节点输入取值（支持 a.b 嵌套路径）；凭据解密后以 credential.* 命名空间暴露给模板。
 * 非 2xx / 网络异常一律上抛 BizException，由引擎按 retryable 重试。
 * 禁止在日志中打印解密后的凭据内容。
 */
@Component
public class HttpConnector implements Connector {

    private static final Logger log = LoggerFactory.getLogger(HttpConnector.class);
    private static final Pattern PLACEHOLDER = Pattern.compile("\\{\\{\\s*([\\w.\\-]+)\\s*}}");

    private final ConnectorCredentialMapper credentialMapper;
    private final CredentialCryptoService cryptoService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public HttpConnector(ConnectorCredentialMapper credentialMapper, CredentialCryptoService cryptoService) {
        this.credentialMapper = credentialMapper;
        this.cryptoService = cryptoService;
    }

    @Override
    public String type() {
        return "http";
    }

    @Override
    public Map<String, Object> execute(Map<String, Object> config, Map<String, Object> input) {
        Map<String, Object> scope = new HashMap<>(input == null ? Map.of() : input);
        // 凭据解密合并进模板作用域（credential.*）
        Object credentialId = config.get("credentialId");
        if (credentialId != null) {
            ConnectorCredential credential = credentialMapper.selectById(((Number) credentialId).longValue());
            if (credential == null) {
                throw new BizException(ErrorCode.CREDENTIAL_NOT_FOUND, String.valueOf(credentialId));
            }
            try {
                String plain = cryptoService.decrypt(credential.getConfigJson());
                @SuppressWarnings("unchecked")
                Map<String, Object> credMap = objectMapper.readValue(plain, Map.class);
                scope.put("credential", credMap);
            } catch (BizException e) {
                throw e;
            } catch (Exception e) {
                throw new BizException(ErrorCode.HTTP_NODE_FAILED, "凭据解密/解析失败");
            }
        }

        String url = render(required(config, "url"), scope);
        String method = String.valueOf(config.getOrDefault("method", "GET")).toUpperCase();
        int timeoutMs = config.get("timeoutMs") instanceof Number n ? n.intValue() : 10_000;

        HttpHeaders headers = new HttpHeaders();
        Object rawHeaders = config.get("headers");
        if (rawHeaders instanceof Map<?, ?> headerMap) {
            headerMap.forEach((k, v) -> headers.add(String.valueOf(k), render(String.valueOf(v), scope)));
        }
        String body = config.get("bodyTemplate") == null ? null
                : render(String.valueOf(config.get("bodyTemplate")), scope);

        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(timeoutMs);
        factory.setReadTimeout(timeoutMs);
        RestTemplate restTemplate = new RestTemplate(factory);

        long start = System.currentTimeMillis();
        try {
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.valueOf(method),
                    new HttpEntity<>(body, headers), String.class);
            long latency = System.currentTimeMillis() - start;
            if (!response.getStatusCode().is2xxSuccessful()) {
                throw new BizException(ErrorCode.HTTP_NODE_FAILED, "HTTP " + response.getStatusCode().value());
            }
            Map<String, Object> output = new HashMap<>();
            output.put("status", response.getStatusCode().value());
            output.put("body", response.getBody());
            output.put("latencyMs", latency);
            return output;
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            // 含 4xx/5xx（RestTemplate 抛 HttpStatusCodeException）与超时/连接异常
            log.warn("http connector call failed url={} err={}", url, e.getMessage());
            throw new BizException(ErrorCode.HTTP_NODE_FAILED, e.getMessage());
        }
    }

    private static String required(Map<String, Object> config, String key) {
        Object v = config.get(key);
        if (v == null || String.valueOf(v).isBlank()) {
            throw new BizException(ErrorCode.DSL_INVALID, "http 节点缺少 config." + key);
        }
        return String.valueOf(v);
    }

    /**
     * {{var}} 模板替换：按点号路径在 scope 中逐级下钻取值，缺失抛参数错误。
     */
    static String render(String template, Map<String, Object> scope) {
        Matcher matcher = PLACEHOLDER.matcher(template);
        StringBuilder sb = new StringBuilder();
        while (matcher.find()) {
            String path = matcher.group(1);
            matcher.appendReplacement(sb, Matcher.quoteReplacement(String.valueOf(resolve(scope, path))));
        }
        matcher.appendTail(sb);
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    private static Object resolve(Map<String, Object> scope, String path) {
        Object current = scope;
        for (String seg : path.split("\\.")) {
            if (!(current instanceof Map)) {
                throw new BizException(ErrorCode.PARAM_ERROR, "模板变量路径不可下钻: " + path);
            }
            current = ((Map<String, Object>) current).get(seg);
            if (current == null) {
                throw new BizException(ErrorCode.PARAM_ERROR, "模板变量缺失: " + path);
            }
        }
        return current;
    }
}
