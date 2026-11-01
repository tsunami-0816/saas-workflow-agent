package com.swa.backend.engine.executor;

import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.config.RabbitConfig;
import com.swa.backend.engine.ExecutionMessage;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

/**
 * 延时节点执行器（BE-4.7）：发送带消息级 expiration 的延时消息到 execution.delay.queue
 * （TTL + DLX 回流 execution.run），引擎将节点置 WAITING 挂起，到期后由 Worker 恢复调度。
 * 非重试：消息已发出后重试会造成重复延时消息。
 */
@Component
public class DelayNodeExecutor implements NodeExecutor {

    /** 延时上限 24h，防止配置错误导致消息长期滞留。 */
    private static final long MAX_DELAY_MS = 24 * 3600_000L;

    private final RabbitTemplate rabbitTemplate;

    public DelayNodeExecutor(RabbitTemplate rabbitTemplate) {
        this.rabbitTemplate = rabbitTemplate;
    }

    @Override
    public String type() {
        return "delay";
    }

    @Override
    public boolean retryable() {
        return false;
    }

    @Override
    public NodeResult execute(NodeContext ctx) {
        Object raw = ctx.getNode().getConfig() == null ? null : ctx.getNode().getConfig().get("delayMs");
        long delayMs = raw instanceof Number n ? n.longValue() : -1;
        if (delayMs <= 0 || delayMs > MAX_DELAY_MS) {
            throw new BizException(ErrorCode.DSL_INVALID,
                    "delay 节点 config.delayMs 须在 (0, 86400000] 毫秒: " + raw);
        }
        ExecutionMessage message = new ExecutionMessage(ctx.getExecutionId(), ctx.getTenantId(), ctx.getNode().getId());
        rabbitTemplate.convertAndSend(RabbitConfig.EXECUTION_EXCHANGE, RabbitConfig.DELAY_ROUTING_KEY, message,
                m -> {
                    m.getMessageProperties().setExpiration(String.valueOf(delayMs));
                    return m;
                });
        return NodeResult.asyncPending();
    }
}
