package com.swa.backend.engine.executor;

import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 节点执行器注册表：按 type 索引全部 NodeExecutor 实现（Spring 自动收集）。
 */
@Component
public class ExecutorRegistry {

    private final Map<String, NodeExecutor> executors = new HashMap<>();

    public ExecutorRegistry(List<NodeExecutor> executorList) {
        for (NodeExecutor executor : executorList) {
            executors.put(executor.type(), executor);
        }
    }

    /**
     * 按节点类型取执行器，未注册抛 20003。
     */
    public NodeExecutor get(String type) {
        NodeExecutor executor = executors.get(type);
        if (executor == null) {
            throw new BizException(ErrorCode.DSL_UNKNOWN_NODE_TYPE, type);
        }
        return executor;
    }
}
