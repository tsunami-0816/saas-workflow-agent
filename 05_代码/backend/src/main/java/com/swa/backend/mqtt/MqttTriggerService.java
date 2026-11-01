package com.swa.backend.mqtt;

import com.swa.backend.common.TenantContext;
import com.swa.backend.entity.MqttSubscription;
import com.swa.backend.mapper.MqttSubscriptionMapper;
import com.swa.backend.service.ExecutionService;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttTopic;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * MQTT 触发器（BE-7.3）：Paho 客户端 QoS1 + cleanSession=false 订阅全部 active topic；
 * 消息到达（打点 start=millis）→ 按 topic 反查订阅（支持 +/# 通配，MqttTopic.isMatched）
 * → 设置 TenantContext → createMqtt 创建执行 → 打 latency 日志（M6 P95≤3s 打点）。
 * broker 不可达时启动不崩溃，仅记 error，resubscribe 时重试连接。
 */
@Service
public class MqttTriggerService {

    private static final Logger log = LoggerFactory.getLogger(MqttTriggerService.class);

    private final MqttSubscriptionMapper subscriptionMapper;
    private final ExecutionService executionService;
    private final String brokerUrl;
    private final String clientId;

    private MqttClient client;
    /** 当前已订阅 topic 集合（resubscribe 做 diff）。 */
    private final Set<String> subscribedTopics = new HashSet<>();

    public MqttTriggerService(MqttSubscriptionMapper subscriptionMapper, ExecutionService executionService,
                              @Value("${mqtt.broker-url}") String brokerUrl,
                              @Value("${mqtt.client-id:swa-backend-main}") String clientId) {
        this.subscriptionMapper = subscriptionMapper;
        this.executionService = executionService;
        this.brokerUrl = brokerUrl;
        this.clientId = clientId;
    }

    @PostConstruct
    public void start() {
        try {
            client = new MqttClient(brokerUrl, clientId, new MemoryPersistence());
            MqttConnectOptions options = new MqttConnectOptions();
            options.setCleanSession(false);
            options.setAutomaticReconnect(true);
            client.setCallback(new org.eclipse.paho.client.mqttv3.MqttCallback() {
                @Override
                public void connectionLost(Throwable cause) {
                    log.warn("mqtt connection lost: {}", cause == null ? "unknown" : cause.getMessage());
                }

                @Override
                public void messageArrived(String topic, org.eclipse.paho.client.mqttv3.MqttMessage message) {
                    onMessage(topic, new String(message.getPayload(), StandardCharsets.UTF_8));
                }

                @Override
                public void deliveryComplete(org.eclipse.paho.client.mqttv3.IMqttDeliveryToken token) {
                    // 纯订阅方，无需处理
                }
            });
            client.connect(options);
            resubscribe();
            log.info("mqtt connected broker={} clientId={}", brokerUrl, clientId);
        } catch (MqttException e) {
            log.error("mqtt connect failed broker={}: {}（订阅将于 resubscribe 时重试）", brokerUrl, e.getMessage());
        }
    }

    /**
     * 全量重订阅：订阅 CRUD 后调用。对已删除/禁用的 topic 取消订阅。
     */
    public synchronized void resubscribe() {
        if (client == null || !client.isConnected()) {
            tryReconnect();
            if (client == null || !client.isConnected()) {
                return;
            }
        }
        List<MqttSubscription> active = subscriptionMapper.selectActiveIgnoreTenant();
        Set<String> target = new HashSet<>();
        for (MqttSubscription sub : active) {
            target.add(sub.getTopic());
        }
        try {
            for (String topic : subscribedTopics) {
                if (!target.contains(topic)) {
                    client.unsubscribe(topic);
                }
            }
            for (String topic : target) {
                client.subscribe(topic, 1);
            }
            subscribedTopics.clear();
            subscribedTopics.addAll(target);
            log.info("mqtt resubscribe done, {} topics", target.size());
        } catch (MqttException e) {
            log.error("mqtt resubscribe failed: {}", e.getMessage());
        }
    }

    private void tryReconnect() {
        try {
            if (client != null) {
                client.reconnect();
            }
        } catch (MqttException e) {
            log.error("mqtt reconnect failed: {}", e.getMessage());
        }
    }

    private void onMessage(String topic, String payload) {
        long start = System.currentTimeMillis();
        List<MqttSubscription> active = subscriptionMapper.selectActiveIgnoreTenant();
        for (MqttSubscription sub : active) {
            if (!MqttTopic.isMatched(sub.getTopic(), topic)) {
                continue;
            }
            TenantContext.setTenantId(sub.getTenantId());
            try {
                executionService.createMqtt(sub, payload);
                log.info("mqtt triggered execution topic={} subscriptionId={} latency={}ms",
                        topic, sub.getId(), System.currentTimeMillis() - start);
            } catch (Exception e) {
                log.error("mqtt trigger failed topic={} subscriptionId={}: {}", topic, sub.getId(), e.getMessage());
            } finally {
                TenantContext.clear();
            }
        }
    }

    @PreDestroy
    public void stop() {
        try {
            if (client != null && client.isConnected()) {
                client.disconnect();
            }
            if (client != null) {
                client.close();
            }
        } catch (MqttException e) {
            log.warn("mqtt close failed: {}", e.getMessage());
        }
    }
}
