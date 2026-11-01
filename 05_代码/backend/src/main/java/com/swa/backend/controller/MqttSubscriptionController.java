package com.swa.backend.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.Result;
import com.swa.backend.dto.MqttSubscriptionRequest;
import com.swa.backend.entity.MqttSubscription;
import com.swa.backend.mqtt.MqttTriggerService;
import com.swa.backend.security.Audit;
import com.swa.backend.security.RequireRole;
import com.swa.backend.service.MqttSubscriptionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * MQTT 订阅管理接口（BE-7.4，dev+）。写操作后触发客户端重订阅。
 */
@Tag(name = "MQTT 订阅")
@RestController
@RequestMapping("/api/v1/mqtt/subscriptions")
public class MqttSubscriptionController {

    private final MqttSubscriptionService subscriptionService;
    private final MqttTriggerService mqttTriggerService;

    public MqttSubscriptionController(MqttSubscriptionService subscriptionService,
                                      MqttTriggerService mqttTriggerService) {
        this.subscriptionService = subscriptionService;
        this.mqttTriggerService = mqttTriggerService;
    }

    @Operation(summary = "订阅分页列表")
    @GetMapping
    @RequireRole({"admin", "dev", "viewer"})
    public Result<Page<MqttSubscription>> page(@RequestParam(defaultValue = "1") int pageNo,
                                               @RequestParam(defaultValue = "20") int pageSize) {
        return Result.ok(subscriptionService.page(pageNo, pageSize));
    }

    @Operation(summary = "订阅详情")
    @GetMapping("/{id}")
    @RequireRole({"admin", "dev", "viewer"})
    public Result<MqttSubscription> get(@PathVariable Long id) {
        return Result.ok(subscriptionService.get(id));
    }

    @Audit(action = "mqtt.subscription.create")
    @Operation(summary = "创建订阅（uk tenant+topic）")
    @PostMapping
    @RequireRole({"admin", "dev"})
    public Result<MqttSubscription> create(@Valid @RequestBody MqttSubscriptionRequest request) {
        MqttSubscription created = subscriptionService.create(request);
        mqttTriggerService.resubscribe();
        return Result.ok(created);
    }

    @Audit(action = "mqtt.subscription.update")
    @Operation(summary = "更新订阅")
    @PutMapping("/{id}")
    @RequireRole({"admin", "dev"})
    public Result<MqttSubscription> update(@PathVariable Long id,
                                           @Valid @RequestBody MqttSubscriptionRequest request) {
        MqttSubscription updated = subscriptionService.update(id, request);
        mqttTriggerService.resubscribe();
        return Result.ok(updated);
    }

    @Audit(action = "mqtt.subscription.delete")
    @Operation(summary = "删除订阅")
    @DeleteMapping("/{id}")
    @RequireRole({"admin", "dev"})
    public Result<Void> delete(@PathVariable Long id) {
        subscriptionService.delete(id);
        mqttTriggerService.resubscribe();
        return Result.ok();
    }
}
