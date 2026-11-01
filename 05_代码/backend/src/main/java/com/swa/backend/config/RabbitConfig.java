package com.swa.backend.config;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.DirectExchange;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.HashMap;
import java.util.Map;

/**
 * RabbitMQ 拓扑：
 * execution.exchange(direct) ── execution.queue（Worker 消费，prefetch 见 application.yml）
 * execution.delay.queue：TTL + DLX 延时队列，消息到期后经 DLX 回流 execution.exchange 恢复调度。
 */
@Configuration
public class RabbitConfig {

    public static final String EXECUTION_EXCHANGE = "execution.exchange";
    public static final String EXECUTION_QUEUE = "execution.queue";
    public static final String EXECUTION_ROUTING_KEY = "execution.run";
    public static final String DELAY_QUEUE = "execution.delay.queue";
    public static final String DELAY_ROUTING_KEY = "execution.delay";

    @Bean
    public DirectExchange executionExchange() {
        return new DirectExchange(EXECUTION_EXCHANGE, true, false);
    }

    @Bean
    public Queue executionQueue() {
        return QueueBuilder.durable(EXECUTION_QUEUE).build();
    }

    @Bean
    public Binding executionBinding() {
        return BindingBuilder.bind(executionQueue()).to(executionExchange()).with(EXECUTION_ROUTING_KEY);
    }

    /**
     * 延时队列：不设队列级 TTL，使用消息级 expiration（延时节点各自时长不同）；
     * 到期后由 DLX 投递回 execution.exchange/execution.run。
     */
    @Bean
    public Queue delayQueue() {
        Map<String, Object> args = new HashMap<>();
        args.put("x-dead-letter-exchange", EXECUTION_EXCHANGE);
        args.put("x-dead-letter-routing-key", EXECUTION_ROUTING_KEY);
        return QueueBuilder.durable(DELAY_QUEUE).withArguments(args).build();
    }

    @Bean
    public Binding delayBinding() {
        return BindingBuilder.bind(delayQueue()).to(executionExchange()).with(DELAY_ROUTING_KEY);
    }
}
