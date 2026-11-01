package com.swa.backend.llm;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

/**
 * 模型路由配置（application.yml llm.*）：
 * routes: taskType → provider 名；price: provider → 单价（每 1K token，元）。
 */
@Component
@ConfigurationProperties(prefix = "llm")
public class LlmProperties {

    private Map<String, String> routes = new HashMap<>();
    private Map<String, String> price = new HashMap<>();

    public Map<String, String> getRoutes() {
        return routes;
    }

    public void setRoutes(Map<String, String> routes) {
        this.routes = routes;
    }

    public Map<String, String> getPrice() {
        return price;
    }

    public void setPrice(Map<String, String> price) {
        this.price = price;
    }
}
