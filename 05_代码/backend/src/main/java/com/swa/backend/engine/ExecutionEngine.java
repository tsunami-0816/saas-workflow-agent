package com.swa.backend.engine;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.swa.backend.common.TenantContext;
import com.swa.backend.engine.dsl.DslDocument;
import com.swa.backend.engine.dsl.DslValidator;
import com.swa.backend.engine.executor.ExecutorRegistry;
import com.swa.backend.engine.executor.NodeContext;
import com.swa.backend.engine.executor.NodeExecutor;
import com.swa.backend.engine.executor.NodeResult;
import com.swa.backend.entity.Execution;
import com.swa.backend.entity.NodeExecution;
import com.swa.backend.entity.WorkflowVersion;
import com.swa.backend.mapper.ExecutionMapper;
import com.swa.backend.mapper.NodeExecutionMapper;
import com.swa.backend.mapper.WorkflowVersionMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * DAG 执行引擎（BE-4 核心）。
 * 调度口径：schedule(executionId, resumeNodeId) 由 MQ Worker 触发——
 * resumeNodeId 为 null 表示新实例从头调度；非 null 表示延时节点到期恢复。
 *
 * 节点状态机：PENDING → RUNNING → SUCCESS/FAILED；WAITING（延时挂起）；SKIPPED（条件未选中分支）。
 * 每次状态变更：写 node_execution + SSE 推送。
 * 可重试节点失败重试 ≤3（退避 1s/2s/4s），重试记录写 retry_log（JSON 数组）。
 * 全部节点终态后 execution → SUCCESS/FAILED；存在 WAITING 节点则 execution → WAITING（挂起等恢复）。
 */
@Service
public class ExecutionEngine {

    private static final Logger log = LoggerFactory.getLogger(ExecutionEngine.class);
    private static final int MAX_RETRY = 3;
    private static final long[] RETRY_BACKOFF_MS = {1000L, 2000L, 4000L};
    private static final Set<String> NODE_TERMINAL = Set.of("SUCCESS", "FAILED", "SKIPPED");

    private final ExecutionMapper executionMapper;
    private final NodeExecutionMapper nodeExecutionMapper;
    private final WorkflowVersionMapper workflowVersionMapper;
    private final DslValidator dslValidator;
    private final ExecutorRegistry executorRegistry;
    private final SseEmitterManager sseEmitterManager;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public ExecutionEngine(ExecutionMapper executionMapper, NodeExecutionMapper nodeExecutionMapper,
                           WorkflowVersionMapper workflowVersionMapper, DslValidator dslValidator,
                           ExecutorRegistry executorRegistry, SseEmitterManager sseEmitterManager) {
        this.executionMapper = executionMapper;
        this.nodeExecutionMapper = nodeExecutionMapper;
        this.workflowVersionMapper = workflowVersionMapper;
        this.dslValidator = dslValidator;
        this.executorRegistry = executorRegistry;
        this.sseEmitterManager = sseEmitterManager;
    }

    /**
     * 调度执行实例。线程安全前提：同一 executionId 同一时刻仅一个 Worker 线程在调度
     * （MQ 串行分发 + 延时消息到期触发；应用内不主动并发 schedule 同一实例）。
     */
    public void schedule(Long executionId, String resumeNodeId) {
        Execution execution = executionMapper.selectByIdIgnoreTenant(executionId);
        if (execution == null) {
            log.warn("execution {} not found, skip", executionId);
            return;
        }
        if ("SUCCESS".equals(execution.getStatus()) || "FAILED".equals(execution.getStatus())) {
            // 终态幂等：重复消息直接丢弃
            return;
        }
        TenantContext.setTenantId(execution.getTenantId());
        try {
            doSchedule(execution, resumeNodeId);
        } catch (Exception e) {
            log.error("engine schedule error executionId={}", executionId, e);
            convergeFailed(execution, "engine_error");
        } finally {
            TenantContext.clear();
        }
    }

    private void doSchedule(Execution execution, String resumeNodeId) {
        WorkflowVersion version = workflowVersionMapper.selectById(execution.getVersionId());
        DslDocument doc = dslValidator.validate(version.getDslJson());
        List<DslDocument.Edge> edges = doc.getEdges() == null ? List.of() : doc.getEdges();

        List<NodeExecution> nodeRows = nodeExecutionMapper.selectList(
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<NodeExecution>()
                        .eq("execution_id", execution.getId()));
        Map<String, NodeExecution> state = nodeRows.stream()
                .collect(Collectors.toMap(NodeExecution::getNodeId, Function.identity()));
        Map<String, DslDocument.Node> dslNodes = doc.getNodes().stream()
                .collect(Collectors.toMap(DslDocument.Node::getId, Function.identity()));

        // 延时恢复：WAITING → SUCCESS
        if (resumeNodeId != null) {
            NodeExecution resumed = state.get(resumeNodeId);
            if (resumed != null && "WAITING".equals(resumed.getStatus())) {
                resumed.setStatus("SUCCESS");
                resumed.setOutputJson("{\"resumed\":true}");
                resumed.setEndedAt(LocalDateTime.now());
                nodeExecutionMapper.updateById(resumed);
                sseEmitterManager.pushNode(execution.getId(), resumed);
            }
            if ("WAITING".equals(execution.getStatus())) {
                execution.setStatus("RUNNING");
                executionMapper.updateById(execution);
                sseEmitterManager.pushExecution(execution.getId(), execution);
            }
        }

        // 调度主循环：每轮找「全部前驱终态」的 PENDING 节点，可达则执行，不可达则 SKIPPED
        boolean progressed = true;
        while (progressed) {
            progressed = false;
            for (DslDocument.Node node : doc.getNodes()) {
                NodeExecution row = state.get(node.getId());
                if (row == null || !"PENDING".equals(row.getStatus())) {
                    continue;
                }
                List<DslDocument.Edge> incoming = edges.stream()
                        .filter(e -> e.getTarget().equals(node.getId())).toList();
                if (!incoming.isEmpty()) {
                    boolean allPredTerminal = incoming.stream()
                            .allMatch(e -> NODE_TERMINAL.contains(state.get(e.getSource()).getStatus()));
                    if (!allPredTerminal) {
                        continue;
                    }
                    if (!reachable(incoming, state, dslNodes)) {
                        markNode(row, "SKIPPED", null, null, null);
                        sseEmitterManager.pushNode(execution.getId(), row);
                        progressed = true;
                        continue;
                    }
                }
                runNode(execution, node, row, incoming, state);
                progressed = true;
                if ("FAILED".equals(row.getStatus())) {
                    // 节点失败：本轮余下节点不再启动，收敛阶段统一 SKIPPED/FAILED
                }
            }
        }

        // 收敛
        boolean anyFailed = state.values().stream().anyMatch(n -> "FAILED".equals(n.getStatus()));
        boolean allTerminal = state.values().stream().allMatch(n -> NODE_TERMINAL.contains(n.getStatus()));
        boolean anyWaiting = state.values().stream().anyMatch(n -> "WAITING".equals(n.getStatus()));
        if (anyFailed) {
            convergeFailed(execution, "node_failed");
        } else if (allTerminal) {
            execution.setStatus("SUCCESS");
            execution.setEndedAt(LocalDateTime.now());
            executionMapper.updateById(execution);
            sseEmitterManager.pushExecution(execution.getId(), execution);
            log.info("execution {} SUCCESS", execution.getId());
        } else if (anyWaiting) {
            execution.setStatus("WAITING");
            executionMapper.updateById(execution);
            sseEmitterManager.pushExecution(execution.getId(), execution);
            log.info("execution {} WAITING (delay pending)", execution.getId());
        } else {
            // 理论不可达（校验已保证无环），兜底防悬挂
            convergeFailed(execution, "engine_deadlock");
        }
    }

    /**
     * 边可达判定：前驱必须 SUCCESS；前驱为 condition 时，edge.branch 必须等于其求值分支。
     */
    private boolean reachable(List<DslDocument.Edge> incoming, Map<String, NodeExecution> state,
                              Map<String, DslDocument.Node> dslNodes) {
        for (DslDocument.Edge edge : incoming) {
            NodeExecution pred = state.get(edge.getSource());
            if (pred == null || !"SUCCESS".equals(pred.getStatus())) {
                continue;
            }
            DslDocument.Node predNode = dslNodes.get(edge.getSource());
            if (predNode != null && "condition".equals(predNode.getType())) {
                String chosen = chosenBranch(pred);
                if (chosen != null && chosen.equals(edge.getBranch())) {
                    return true;
                }
            } else {
                return true;
            }
        }
        return false;
    }

    private String chosenBranch(NodeExecution conditionRow) {
        try {
            Map<String, Object> output = objectMapper.readValue(conditionRow.getOutputJson(),
                    new TypeReference<>() {
                    });
            Object branch = output.get("branch");
            return branch == null ? null : (Boolean.parseBoolean(String.valueOf(branch)) ? "true" : "false");
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 执行单节点：写 RUNNING → 调执行器（含重试）→ 写终态。每次变更落库 + SSE。
     */
    private void runNode(Execution execution, DslDocument.Node node, NodeExecution row,
                         List<DslDocument.Edge> incoming, Map<String, NodeExecution> state) {
        NodeExecutor executor = executorRegistry.get(node.getType());
        Map<String, Object> input = buildInput(execution, incoming, state);

        row.setStatus("RUNNING");
        row.setStartedAt(LocalDateTime.now());
        row.setInputJson(writeJson(input));
        nodeExecutionMapper.updateById(row);
        sseEmitterManager.pushNode(execution.getId(), row);

        NodeContext ctx = new NodeContext();
        ctx.setExecutionId(execution.getId());
        ctx.setTenantId(execution.getTenantId());
        ctx.setNode(node);
        ctx.setInput(input);

        int maxAttempts = executor.retryable() ? MAX_RETRY + 1 : 1;
        List<Map<String, Object>> retryLog = new ArrayList<>();
        NodeResult result = null;
        String error = null;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                result = executor.execute(ctx);
                error = result.isSuccess() ? null : result.getErrorMessage();
            } catch (Exception e) {
                result = null;
                error = e.getMessage();
            }
            if (error == null && result != null) {
                break;
            }
            if (attempt < maxAttempts) {
                Map<String, Object> entry = new LinkedHashMap<>();
                entry.put("attempt", attempt);
                entry.put("at", LocalDateTime.now().toString());
                entry.put("error", error);
                retryLog.add(entry);
                try {
                    Thread.sleep(RETRY_BACKOFF_MS[attempt - 1]);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    error = "interrupted";
                    break;
                }
            }
        }

        if (result != null && result.isSuccess() && result.isAsync()) {
            // 异步挂起（延时节点）：消息已发，等待到期恢复
            row.setStatus("WAITING");
            nodeExecutionMapper.updateById(row);
            sseEmitterManager.pushNode(execution.getId(), row);
            return;
        }
        if (result != null && result.isSuccess()) {
            markNode(row, "SUCCESS", writeJson(result.getOutput()), null, writeJson(retryLog));
            sseEmitterManager.pushNode(execution.getId(), row);
            return;
        }
        // 最终失败
        Map<String, Object> last = new LinkedHashMap<>();
        last.put("attempt", maxAttempts);
        last.put("at", LocalDateTime.now().toString());
        last.put("error", error);
        retryLog.add(last);
        markNode(row, "FAILED", null, error, writeJson(retryLog));
        sseEmitterManager.pushNode(execution.getId(), row);
        log.warn("execution {} node {} FAILED: {}", execution.getId(), node.getId(), error);
    }

    private Map<String, Object> buildInput(Execution execution, List<DslDocument.Edge> incoming,
                                           Map<String, NodeExecution> state) {
        Map<String, Object> input = new LinkedHashMap<>();
        // 所有节点：注入触发入参（payload 为前端契约别名，_payload 保留兼容）
        Object parsed = parsePayload(execution.getTriggerPayload());
        input.put("_payload", parsed);
        input.put("payload", parsed);
        if (incoming.isEmpty()) {
            return input;
        }
        // 下游节点：注入全部已完成祖先节点输出（按 nodeId 键），支持跨级引用（如分支下游取 t1.payload.temp）。
        // 2026-10-31 修复：原先仅注入直接前驱输出，分支下游引用触发节点变量时报 Could not find variable。
        for (Map.Entry<String, NodeExecution> e : state.entrySet()) {
            NodeExecution pred = e.getValue();
            if (pred != null && "SUCCESS".equals(pred.getStatus()) && pred.getOutputJson() != null) {
                input.put(pred.getNodeId(), parseMap(pred.getOutputJson()));
            }
        }
        return input;
    }

    private Object parsePayload(String payloadJson) {
        if (payloadJson == null || payloadJson.isBlank()) {
            return Map.of();
        }
        try {
            return objectMapper.readValue(payloadJson, new TypeReference<Map<String, Object>>() {
            });
        } catch (Exception e) {
            return payloadJson;
        }
    }

    private Map<String, Object> parseMap(String json) {
        try {
            return objectMapper.readValue(json, new TypeReference<>() {
            });
        } catch (Exception e) {
            return Map.of("raw", json);
        }
    }

    private void markNode(NodeExecution row, String status, String outputJson, String errorMessage, String retryLog) {
        row.setStatus(status);
        if (outputJson != null) {
            row.setOutputJson(outputJson);
        }
        if (errorMessage != null) {
            row.setErrorMessage(errorMessage.length() > 1000 ? errorMessage.substring(0, 1000) : errorMessage);
        }
        if (retryLog != null) {
            row.setRetryLog(retryLog);
        }
        if (NODE_TERMINAL.contains(status)) {
            row.setEndedAt(LocalDateTime.now());
        }
        nodeExecutionMapper.updateById(row);
    }

    private void convergeFailed(Execution execution, String failReason) {
        execution.setStatus("FAILED");
        execution.setFailReason(failReason);
        execution.setEndedAt(LocalDateTime.now());
        executionMapper.updateById(execution);
        sseEmitterManager.pushExecution(execution.getId(), execution);
        log.info("execution {} FAILED reason={}", execution.getId(), failReason);
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            return "{}";
        }
    }
}
