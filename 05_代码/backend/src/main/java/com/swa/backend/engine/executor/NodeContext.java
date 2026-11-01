package com.swa.backend.engine.executor;

import com.swa.backend.engine.dsl.DslDocument;

import java.util.Map;

/**
 * 节点执行上下文。
 */
public class NodeContext {

    private Long executionId;
    private Long tenantId;
    private DslDocument.Node node;
    /** 节点输入：上游输出合并（key=上游 nodeId）+ _payload（起点触发入参）。 */
    private Map<String, Object> input;

    public Long getExecutionId() {
        return executionId;
    }

    public void setExecutionId(Long executionId) {
        this.executionId = executionId;
    }

    public Long getTenantId() {
        return tenantId;
    }

    public void setTenantId(Long tenantId) {
        this.tenantId = tenantId;
    }

    public DslDocument.Node getNode() {
        return node;
    }

    public void setNode(DslDocument.Node node) {
        this.node = node;
    }

    public Map<String, Object> getInput() {
        return input;
    }

    public void setInput(Map<String, Object> input) {
        this.input = input;
    }
}
