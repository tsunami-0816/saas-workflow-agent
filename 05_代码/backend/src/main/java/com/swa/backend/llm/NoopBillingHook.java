package com.swa.backend.llm;

import com.swa.backend.entity.LlmCallLog;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

/**
 * BillingHook 空实现（扩展锚点）：不做事，仅占位注册。
 */
@Component
public class NoopBillingHook implements BillingHook {

    @Override
    public void beforeCharge(Long tenantId, LlmCallLog callLog) {
        // 扩展锚点：接入计费系统时实现
    }

    @Override
    public void afterCharge(Long tenantId, LlmCallLog callLog, BigDecimal cost) {
        // 扩展锚点：接入计费系统时实现
    }
}
