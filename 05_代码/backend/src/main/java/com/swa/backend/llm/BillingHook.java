package com.swa.backend.llm;

import com.swa.backend.entity.LlmCallLog;

import java.math.BigDecimal;

/**
 * 计费钩子（扩展锚点，BE-6.5）：默认 NoopBillingHook 空实现。
 * 接入真实计费/出账系统时实现本接口并替换注册。
 */
public interface BillingHook {

    /**
     * 计费前回调（provider 调用成功后、额度扣减前）。
     *
     * @param tenantId 租户 id
     * @param callLog  已填充 token/成本的台账记录（未落库）
     */
    void beforeCharge(Long tenantId, LlmCallLog callLog);

    /**
     * 计费完成后回调（台账落库 + 额度扣减成功）。
     *
     * @param tenantId 租户 id
     * @param callLog  台账记录
     * @param cost     本次成本
     */
    void afterCharge(Long tenantId, LlmCallLog callLog, BigDecimal cost);
}
