package com.swa.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** MQTT 订阅创建/更新请求。 */
public record MqttSubscriptionRequest(
        @NotBlank @Size(max = 256) String topic,
        @NotNull Long workflowVersionId,
        @Pattern(regexp = "active|disabled") String status) {
}
