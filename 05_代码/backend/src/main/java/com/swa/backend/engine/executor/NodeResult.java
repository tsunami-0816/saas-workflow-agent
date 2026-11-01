package com.swa.backend.engine.executor;

import java.util.Map;

/**
 * 节点执行结果。async=true 表示异步挂起（延时节点），引擎暂停调度等待恢复消息。
 */
public class NodeResult {

    private boolean success;
    private boolean async;
    private Map<String, Object> output;
    private String errorMessage;

    public static NodeResult ok(Map<String, Object> output) {
        NodeResult r = new NodeResult();
        r.success = true;
        r.output = output;
        return r;
    }

    public static NodeResult fail(String errorMessage) {
        NodeResult r = new NodeResult();
        r.success = false;
        r.errorMessage = errorMessage;
        return r;
    }

    public static NodeResult asyncPending() {
        NodeResult r = new NodeResult();
        r.success = true;
        r.async = true;
        return r;
    }

    public boolean isSuccess() {
        return success;
    }

    public boolean isAsync() {
        return async;
    }

    public Map<String, Object> getOutput() {
        return output;
    }

    public String getErrorMessage() {
        return errorMessage;
    }
}
