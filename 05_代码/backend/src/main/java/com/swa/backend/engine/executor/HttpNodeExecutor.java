package com.swa.backend.engine.executor;

import com.swa.backend.connector.ConnectorRegistry;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * HTTP 节点执行器：委托 http 连接器完成真实调用（重试由引擎统一处理）。
 */
@Component
public class HttpNodeExecutor implements NodeExecutor {

    private final ConnectorRegistry connectorRegistry;

    public HttpNodeExecutor(ConnectorRegistry connectorRegistry) {
        this.connectorRegistry = connectorRegistry;
    }

    @Override
    public String type() {
        return "http";
    }

    @Override
    public NodeResult execute(NodeContext ctx) {
        Map<String, Object> output = connectorRegistry.get("http")
                .execute(ctx.getNode().getConfig(), ctx.getInput());
        return NodeResult.ok(output);
    }
}
