package com.swa.backend.engine.dsl;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import org.springframework.stereotype.Component;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * DSL 校验器（BE-3.2）：
 * 1. JSON 可解析且含 nodes/edges；
 * 2. 节点类型合法（http/condition/code/delay/agent/mqtt-trigger）；
 * 3. 连线两端节点必须存在（悬空拒收）；
 * 4. 入出度合法（mqtt-trigger 入度必须 0；condition 出度 ≥1 且分支标记 true/false；普通节点出度不限）；
 * 5. 无环（Kahn 拓扑检测）。
 * 校验失败抛出对应 2xxxx 错误码。
 */
@Component
public class DslValidator {

    /** 合法节点类型集合。 */
    public static final Set<String> NODE_TYPES = Set.of(
            "http", "condition", "code", "delay", "agent", "mqtt-trigger");

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 解析并校验 DSL，返回结构化文档。
     *
     * @param dslJson 画布导出的 DSL JSON 文本
     * @return 校验通过的 DslDocument
     */
    public DslDocument validate(String dslJson) {
        DslDocument doc;
        try {
            doc = objectMapper.readValue(dslJson, DslDocument.class);
        } catch (Exception e) {
            throw new BizException(ErrorCode.DSL_INVALID, "JSON 解析失败: " + e.getMessage());
        }
        if (doc.getNodes() == null || doc.getNodes().isEmpty()) {
            throw new BizException(ErrorCode.DSL_INVALID, "nodes 不能为空");
        }
        List<DslDocument.Edge> edges = doc.getEdges() == null ? List.of() : doc.getEdges();

        // 节点 id 唯一 + 类型合法
        Map<String, DslDocument.Node> nodeMap = new LinkedHashMap<>();
        for (DslDocument.Node node : doc.getNodes()) {
            if (node.getId() == null || node.getId().isBlank()) {
                throw new BizException(ErrorCode.DSL_INVALID, "节点 id 不能为空");
            }
            if (!nodeMap.containsKey(node.getId())) {
                nodeMap.put(node.getId(), node);
            } else {
                throw new BizException(ErrorCode.DSL_INVALID, "节点 id 重复: " + node.getId());
            }
            if (node.getType() == null || !NODE_TYPES.contains(node.getType())) {
                throw new BizException(ErrorCode.DSL_UNKNOWN_NODE_TYPE,
                        "node=" + node.getId() + " type=" + node.getType());
            }
        }

        // 连线端点存在性 + 入出度统计
        Map<String, Integer> inDegree = new HashMap<>();
        Map<String, Integer> outDegree = new HashMap<>();
        Map<String, List<DslDocument.Edge>> outgoing = new HashMap<>();
        nodeMap.keySet().forEach(id -> {
            inDegree.put(id, 0);
            outDegree.put(id, 0);
            outgoing.put(id, new ArrayList<>());
        });
        for (DslDocument.Edge edge : edges) {
            if (edge.getSource() == null || edge.getTarget() == null
                    || !nodeMap.containsKey(edge.getSource()) || !nodeMap.containsKey(edge.getTarget())) {
                throw new BizException(ErrorCode.DSL_DANGLING_EDGE,
                        "edge " + edge.getSource() + " -> " + edge.getTarget());
            }
            if (edge.getSource().equals(edge.getTarget())) {
                throw new BizException(ErrorCode.DSL_CYCLE, "自环: " + edge.getSource());
            }
            inDegree.merge(edge.getTarget(), 1, Integer::sum);
            outDegree.merge(edge.getSource(), 1, Integer::sum);
            outgoing.get(edge.getSource()).add(edge);
        }

        for (DslDocument.Node node : doc.getNodes()) {
            int in = inDegree.get(node.getId());
            int out = outDegree.get(node.getId());
            switch (node.getType()) {
                case "mqtt-trigger" -> {
                    if (in != 0) {
                        throw new BizException(ErrorCode.DSL_DEGREE_INVALID,
                                "mqtt-trigger 节点不允许有入边: " + node.getId());
                    }
                }
                case "condition" -> {
                    if (out < 1) {
                        throw new BizException(ErrorCode.DSL_DEGREE_INVALID,
                                "condition 节点必须有出边: " + node.getId());
                    }
                    Set<String> branches = new HashSet<>();
                    for (DslDocument.Edge e : outgoing.get(node.getId())) {
                        if (!"true".equals(e.getBranch()) && !"false".equals(e.getBranch())) {
                            throw new BizException(ErrorCode.DSL_DEGREE_INVALID,
                                    "condition 出边必须标记 branch=true/false: " + node.getId());
                        }
                        branches.add(e.getBranch());
                    }
                    if (!branches.contains("true") || !branches.contains("false")) {
                        throw new BizException(ErrorCode.DSL_DEGREE_INVALID,
                                "condition 节点需同时覆盖 true/false 分支: " + node.getId());
                    }
                }
                default -> {
                    if (in == 0 && out == 0 && doc.getNodes().size() > 1) {
                        throw new BizException(ErrorCode.DSL_DEGREE_INVALID,
                                "孤立节点: " + node.getId());
                    }
                }
            }
        }

        // 无环检测（Kahn）
        Map<String, Integer> remainingIn = new HashMap<>(inDegree);
        Deque<String> queue = new ArrayDeque<>();
        remainingIn.forEach((id, d) -> {
            if (d == 0) {
                queue.offer(id);
            }
        });
        int visited = 0;
        while (!queue.isEmpty()) {
            String id = queue.poll();
            visited++;
            for (DslDocument.Edge e : outgoing.get(id)) {
                int d = remainingIn.merge(e.getTarget(), -1, Integer::sum);
                if (d == 0) {
                    queue.offer(e.getTarget());
                }
            }
        }
        if (visited != nodeMap.size()) {
            throw new BizException(ErrorCode.DSL_CYCLE);
        }
        return doc;
    }
}
