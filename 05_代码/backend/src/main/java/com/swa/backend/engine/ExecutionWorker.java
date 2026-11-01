package com.swa.backend.engine;

import com.swa.backend.config.RabbitConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

/**
 * 执行 Worker（BE-4.3）：消费 execution.queue，驱动引擎调度。
 * traceId = executionId，贯穿日志（BE-10.1）。并发 16 由监听容器配置保证。
 */
@Component
public class ExecutionWorker {

    private static final Logger log = LoggerFactory.getLogger(ExecutionWorker.class);

    private final ExecutionEngine executionEngine;

    public ExecutionWorker(ExecutionEngine executionEngine) {
        this.executionEngine = executionEngine;
    }

    @RabbitListener(queues = RabbitConfig.EXECUTION_QUEUE)
    public void onMessage(ExecutionMessage message) {
        MDC.put("traceId", String.valueOf(message.executionId()));
        try {
            log.info("worker receive executionId={} resumeNodeId={}", message.executionId(), message.resumeNodeId());
            executionEngine.schedule(message.executionId(), message.resumeNodeId());
        } catch (Exception e) {
            // 引擎内部已兜底收敛；这里仅防消息无限重回队列
            log.error("worker handle failed executionId={}: {}", message.executionId(), e.getMessage());
        } finally {
            MDC.remove("traceId");
        }
    }
}
