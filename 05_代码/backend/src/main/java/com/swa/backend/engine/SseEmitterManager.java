package com.swa.backend.engine;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * SSE 推送管理（BE-4.9）：executionId → 订阅者列表。
 * 事件名：node（节点状态变更）/ execution（执行终态）/ connected（订阅建立）。
 * emitter 30 分钟超时，异常即剔除，发送失败不阻断引擎。
 */
@Component
public class SseEmitterManager {

    private static final Logger log = LoggerFactory.getLogger(SseEmitterManager.class);
    private static final long TIMEOUT_MS = 30 * 60_000L;

    private final Map<Long, List<SseEmitter>> emitters = new ConcurrentHashMap<>();

    /**
     * 订阅某执行的实时事件。
     */
    public SseEmitter subscribe(Long executionId) {
        SseEmitter emitter = new SseEmitter(TIMEOUT_MS);
        List<SseEmitter> list = emitters.computeIfAbsent(executionId, k -> new CopyOnWriteArrayList<>());
        list.add(emitter);
        emitter.onCompletion(() -> remove(executionId, emitter));
        emitter.onTimeout(() -> remove(executionId, emitter));
        emitter.onError(e -> remove(executionId, emitter));
        try {
            emitter.send(SseEmitter.event().name("connected").data("ok"));
        } catch (IOException e) {
            remove(executionId, emitter);
        }
        return emitter;
    }

    /**
     * 推送节点状态变更事件。
     */
    public void pushNode(Long executionId, Object nodeExecution) {
        push(executionId, "node", nodeExecution);
    }

    /**
     * 推送执行整体状态事件。
     */
    public void pushExecution(Long executionId, Object execution) {
        push(executionId, "execution", execution);
    }

    private void push(Long executionId, String event, Object data) {
        List<SseEmitter> list = emitters.get(executionId);
        if (list == null || list.isEmpty()) {
            return;
        }
        for (SseEmitter emitter : list) {
            try {
                emitter.send(SseEmitter.event().name(event).data(data));
            } catch (Exception e) {
                log.debug("sse push failed, drop emitter: {}", e.getMessage());
                remove(executionId, emitter);
            }
        }
    }

    private void remove(Long executionId, SseEmitter emitter) {
        List<SseEmitter> list = emitters.get(executionId);
        if (list != null) {
            list.remove(emitter);
            if (list.isEmpty()) {
                emitters.remove(executionId, list);
            }
        }
    }
}
