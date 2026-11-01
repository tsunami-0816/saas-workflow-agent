package com.swa.backend.engine.executor;

import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * MQTT 触发节点执行器：占位直通，把触发入参（_payload）原样输出给下游。
 * 真正的订阅/反查逻辑见 mqtt.MqttTriggerService。
 */
@Component
public class MqttTriggerNodeExecutor implements NodeExecutor {

    @Override
    public String type() {
        return "mqtt-trigger";
    }

    @Override
    public boolean retryable() {
        return false;
    }

    @Override
    public NodeResult execute(NodeContext ctx) {
        Object payload = ctx.getInput() == null ? null : ctx.getInput().get("_payload");
        return NodeResult.ok(Map.of("payload", payload == null ? Map.of() : payload));
    }
}
