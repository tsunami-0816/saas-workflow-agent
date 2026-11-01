package com.swa.backend.engine.executor;

/**
 * 节点执行器 SPI（扩展锚点）：新增节点类型 = 新增实现类注册进 ExecutorRegistry，不动引擎主流程。
 */
public interface NodeExecutor {

    /**
     * 节点类型标识（与 DSL node.type 对应）。
     */
    String type();

    /**
     * 是否允许失败重试（重试 ≤3，退避 1s/2s/4s）。
     */
    default boolean retryable() {
        return true;
    }

    /**
     * 执行节点。
     *
     * @param ctx 节点上下文（节点配置 + 合并后的输入）
     * @return 执行结果
     */
    NodeResult execute(NodeContext ctx);
}
