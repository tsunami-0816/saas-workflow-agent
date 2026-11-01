package com.swa.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.common.TenantContext;
import com.swa.backend.config.RabbitConfig;
import com.swa.backend.engine.ExecutionMessage;
import com.swa.backend.engine.dsl.DslDocument;
import com.swa.backend.engine.dsl.DslValidator;
import com.swa.backend.dto.ExecutionCreateRequest;
import com.swa.backend.entity.Execution;
import com.swa.backend.entity.MqttSubscription;
import com.swa.backend.entity.NodeExecution;
import com.swa.backend.entity.WorkflowVersion;
import com.swa.backend.mapper.ExecutionMapper;
import com.swa.backend.mapper.NodeExecutionMapper;
import com.swa.backend.mapper.WorkflowVersionMapper;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.DigestUtils;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 执行实例服务（BE-4.2 / BE-5）。
 * 幂等键 exec:idem:{userId}:{versionId}:{clientReqId} SETNX TTL 24h，值为 executionId。
 */
@Service
public class ExecutionService {

    private static final Duration IDEM_TTL = Duration.ofHours(24);

    private final ExecutionMapper executionMapper;
    private final NodeExecutionMapper nodeExecutionMapper;
    private final WorkflowVersionMapper versionMapper;
    private final DslValidator dslValidator;
    private final RedisTemplate<String, String> redisTemplate;
    private final RabbitTemplate rabbitTemplate;

    public ExecutionService(ExecutionMapper executionMapper, NodeExecutionMapper nodeExecutionMapper,
                            WorkflowVersionMapper versionMapper, DslValidator dslValidator,
                            RedisTemplate<String, String> redisTemplate, RabbitTemplate rabbitTemplate) {
        this.executionMapper = executionMapper;
        this.nodeExecutionMapper = nodeExecutionMapper;
        this.versionMapper = versionMapper;
        this.dslValidator = dslValidator;
        this.redisTemplate = redisTemplate;
        this.rabbitTemplate = rabbitTemplate;
    }

    /**
     * 手工触发执行（幂等）。
     */
    public Execution create(ExecutionCreateRequest request, Long userId) {
        WorkflowVersion version = checkExecutable(request.versionId());
        return doCreate(version, request.clientReqId(), request.triggerPayload(), userId, "manual");
    }

    /**
     * MQTT 触发执行（BE-7.3）。调用方须先设置 TenantContext 为订阅所属租户。
     * 幂等键：mqtt-{subscriptionId}-{md5(payload)}，QoS1 重复投递天然去重。
     */
    public Execution createMqtt(MqttSubscription subscription, String payload) {
        WorkflowVersion version = checkExecutable(subscription.getWorkflowVersionId());
        String clientReqId = "mqtt-" + subscription.getId() + "-"
                + DigestUtils.md5DigestAsHex(payload.getBytes(StandardCharsets.UTF_8));
        return doCreate(version, clientReqId, payload, null, "mqtt");
    }

    /**
     * 回放（BE-5.2）：按历史执行原参数重新触发，产生新实例。
     */
    public Execution replay(Long executionId, Long userId) {
        Execution old = get(executionId);
        WorkflowVersion version = checkExecutable(old.getVersionId());
        String clientReqId = "replay-" + old.getId() + "-" + System.currentTimeMillis();
        return doCreate(version, clientReqId, old.getTriggerPayload(), userId, "replay");
    }

    /**
     * 版本可执行性检查：disabled → 20008；非 published → 20009。
     */
    private WorkflowVersion checkExecutable(Long versionId) {
        WorkflowVersion version = versionMapper.selectById(versionId);
        if (version == null) {
            throw new BizException(ErrorCode.VERSION_NOT_FOUND);
        }
        if ("disabled".equals(version.getStatus())) {
            throw new BizException(ErrorCode.VERSION_DISABLED);
        }
        if (!"published".equals(version.getStatus())) {
            throw new BizException(ErrorCode.VERSION_NOT_PUBLISHED, "当前状态=" + version.getStatus());
        }
        return version;
    }

    /**
     * 创建执行：SETNX 幂等 → execution RUNNING 落库 → 节点 PENDING 全量落库 → 发 MQ。
     * 幂等命中直接返回已有实例。
     */
    @Transactional
    public Execution doCreate(WorkflowVersion version, String clientReqId, String triggerPayload,
                              Long userId, String triggerType) {
        Long tenantId = TenantContext.getTenantId();
        String idemKey = "exec:idem:" + (userId == null ? "sys" : userId) + ":" + version.getId() + ":" + clientReqId;
        Boolean first = redisTemplate.opsForValue().setIfAbsent(idemKey, "", IDEM_TTL);
        if (Boolean.FALSE.equals(first)) {
            String existingId = redisTemplate.opsForValue().get(idemKey);
            if (existingId != null && !existingId.isBlank()) {
                // 幂等命中：返回已有实例
                return executionMapper.selectById(Long.parseLong(existingId));
            }
            // 极端情况：上次 SETNX 后写库前崩溃，占坑无 id。拒绝本次，避免双实例。
            throw new BizException(ErrorCode.EXECUTION_CREATE_FAILED, "幂等键冲突，请更换 clientReqId 重试");
        }

        Execution execution = new Execution();
        execution.setTenantId(tenantId);
        execution.setVersionId(version.getId());
        execution.setUserId(userId);
        execution.setStatus("RUNNING");
        execution.setTriggerType(triggerType);
        execution.setTriggerPayload(triggerPayload);
        execution.setStartedAt(LocalDateTime.now());
        executionMapper.insert(execution);

        DslDocument doc = dslValidator.validate(version.getDslJson());
        for (DslDocument.Node node : doc.getNodes()) {
            NodeExecution row = new NodeExecution();
            row.setTenantId(tenantId);
            row.setExecutionId(execution.getId());
            row.setNodeId(node.getId());
            row.setNodeType(node.getType());
            row.setStatus("PENDING");
            nodeExecutionMapper.insert(row);
        }

        // 写库成功后回填幂等值（保留 TTL）
        redisTemplate.opsForValue().set(idemKey, String.valueOf(execution.getId()), IDEM_TTL);
        rabbitTemplate.convertAndSend(RabbitConfig.EXECUTION_EXCHANGE, RabbitConfig.EXECUTION_ROUTING_KEY,
                new ExecutionMessage(execution.getId(), tenantId, null));
        return execution;
    }

    public Page<Execution> page(int pageNo, int pageSize, String status) {
        QueryWrapper<Execution> wrapper = new QueryWrapper<>();
        if (status != null && !status.isBlank()) {
            wrapper.eq("status", status);
        }
        wrapper.orderByDesc("id");
        return executionMapper.selectPage(new Page<>(pageNo, pageSize), wrapper);
    }

    public Execution get(Long id) {
        Execution execution = executionMapper.selectById(id);
        if (execution == null) {
            throw new BizException(ErrorCode.EXECUTION_NOT_FOUND);
        }
        return execution;
    }

    /**
     * 节点快照（BE-4.11）：SSE 断线后先拉快照再续订。
     */
    public List<NodeExecution> nodes(Long executionId) {
        get(executionId);
        return nodeExecutionMapper.selectList(new QueryWrapper<NodeExecution>()
                .eq("execution_id", executionId).orderByAsc("id"));
    }
}
