package com.swa.backend.engine.executor;

import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

/**
 * Agent 任务节点执行器（BE-4.8）：POST ${PYTHON_AGENT_URL}/agent/run，超时 120s。
 * 口径（与 python 侧契约一致）：接口恒返回 HTTP 200，成败看 status 字段；
 * status=FAILED 按节点失败处理（写 retry_log），网络/超时异常上抛由引擎重试。
 */
@Component
public class AgentNodeExecutor implements NodeExecutor {

    private final RestTemplate restTemplate;
    private final String pythonAgentUrl;

    public AgentNodeExecutor(@Value("${integration.python-agent-url}") String pythonAgentUrl) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(120_000);
        this.restTemplate = new RestTemplate(factory);
        this.pythonAgentUrl = pythonAgentUrl;
    }

    @Override
    public String type() {
        return "agent";
    }

    @Override
    public NodeResult execute(NodeContext ctx) {
        String task = ConditionNodeExecutor.configString(ctx, "task");
        Map<String, Object> body = new HashMap<>();
        body.put("executionId", String.valueOf(ctx.getExecutionId()));
        body.put("nodeId", ctx.getNode().getId());
        // 租户透传：python 侧调 /internal/llm/chat 时据此带 X-Tenant-Id，启用额度扣减与台账归租
        body.put("tenantId", ctx.getTenantId());
        body.put("task", task);
        body.put("inputData", ctx.getInput() == null ? Map.of() : ctx.getInput());
        Object constraints = ctx.getNode().getConfig().get("constraints");
        body.put("constraints", constraints instanceof Map ? constraints : Map.of());
        Object taskType = ctx.getNode().getConfig().get("taskType");
        if (taskType != null) {
            body.put("taskType", String.valueOf(taskType));
        }

        Map<?, ?> response = restTemplate.postForObject(pythonAgentUrl + "/agent/run", body, Map.class);
        if (response == null) {
            return NodeResult.fail("agent 响应为空");
        }
        Object status = response.get("status");
        if ("SUCCESS".equals(String.valueOf(status))) {
            Map<String, Object> output = new HashMap<>();
            output.put("output", response.get("output"));
            output.put("reasoning", response.get("reasoning"));
            output.put("durationMs", response.get("durationMs"));
            return NodeResult.ok(output);
        }
        return NodeResult.fail("agent FAILED: " + response.get("error"));
    }
}
