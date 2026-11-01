package com.swa.backend.llm;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.common.LoginUser;
import com.swa.backend.common.TenantContext;
import com.swa.backend.dto.LlmChatRequest;
import com.swa.backend.dto.LlmChatResponse;
import com.swa.backend.entity.LlmCallLog;
import com.swa.backend.entity.TenantQuota;
import com.swa.backend.mapper.LlmCallLogMapper;
import com.swa.backend.mapper.TenantQuotaMapper;
import com.swa.backend.service.TenantService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 模型路由层（BE-6）：taskType → provider 配置路由（可用 request.provider 强制指定）；
 * token × 单价（每 1K）算成本写 llm_call_log（M4 台账）；Redis Lua 原子扣减
 * quota:remain:{tenantId}（不足返回 -1 → 抛 40429/HTTP 429）；同步 tenant_quota.token_used；
 * BillingHook 为扩展锚点。
 */
@Service
public class LlmRouterService {

    private static final Logger log = LoggerFactory.getLogger(LlmRouterService.class);

    /**
     * 额度扣减 Lua：key 不存在时用 ARGV[2]（DB 剩余额度）初始化；
     * 余额不足返回 -1，否则 DECRBY 并返回剩余。
     */
    private static final DefaultRedisScript<Long> DEDUCT_SCRIPT = new DefaultRedisScript<>(
            "local remain = tonumber(redis.call('GET', KEYS[1]) or '-1') "
                    + "if remain < 0 then redis.call('SET', KEYS[1], ARGV[2]) remain = tonumber(ARGV[2]) end "
                    + "if remain < tonumber(ARGV[1]) then return -1 end "
                    + "redis.call('DECRBY', KEYS[1], ARGV[1]) "
                    + "return remain - tonumber(ARGV[1])",
            Long.class);

    private final Map<String, LlmProvider> providers = new HashMap<>();
    private final LlmProperties llmProperties;
    private final LlmCallLogMapper llmCallLogMapper;
    private final TenantQuotaMapper tenantQuotaMapper;
    private final RedisTemplate<String, String> redisTemplate;
    private final BillingHook billingHook;

    public LlmRouterService(List<LlmProvider> providerList, LlmProperties llmProperties,
                            LlmCallLogMapper llmCallLogMapper, TenantQuotaMapper tenantQuotaMapper,
                            RedisTemplate<String, String> redisTemplate, BillingHook billingHook) {
        for (LlmProvider provider : providerList) {
            providers.put(provider.name(), provider);
        }
        this.llmProperties = llmProperties;
        this.llmCallLogMapper = llmCallLogMapper;
        this.tenantQuotaMapper = tenantQuotaMapper;
        this.redisTemplate = redisTemplate;
        this.billingHook = billingHook;
    }

    /**
     * 统一对话入口。
     *
     * @param request taskType/messages/provider(可选强制)
     * @return 统一响应
     */
    public LlmChatResponse chat(LlmChatRequest request) {
        Long tenantId = TenantContext.getTenantId();
        LoginUser loginUser = TenantContext.getLoginUser();
        Long userId = loginUser == null ? null : loginUser.getUserId();

        String providerName = request.provider() != null && !request.provider().isBlank()
                ? request.provider()
                : llmProperties.getRoutes().get(request.taskType());
        if (providerName == null) {
            throw new BizException(ErrorCode.LLM_UNKNOWN_TASK_TYPE, request.taskType());
        }
        LlmProvider provider = providers.get(providerName);
        if (provider == null) {
            throw new BizException(ErrorCode.LLM_UNKNOWN_TASK_TYPE, "provider 未注册: " + providerName);
        }

        long start = System.currentTimeMillis();
        LlmResult result = provider.chat(request.messages());
        long latency = System.currentTimeMillis() - start;

        int totalTokens = result.promptTokens() + result.completionTokens();
        BigDecimal unitPrice = new BigDecimal(llmProperties.getPrice().getOrDefault(providerName, "0"));
        BigDecimal cost = unitPrice.multiply(BigDecimal.valueOf(totalTokens))
                .divide(BigDecimal.valueOf(1000), 6, RoundingMode.HALF_UP);

        LlmCallLog callLog = new LlmCallLog();
        // 内部调用（python-agent）可能无租户上下文：tenantId=0 占位并在日志显式标注（接口文档已声明）
        callLog.setTenantId(tenantId == null ? 0L : tenantId);
        callLog.setUserId(userId);
        callLog.setProvider(providerName);
        callLog.setModel(result.model());
        callLog.setTaskType(request.taskType());
        callLog.setPromptTokens(result.promptTokens());
        callLog.setCompletionTokens(result.completionTokens());
        callLog.setCost(cost);
        callLog.setLatencyMs(latency);

        billingHook.beforeCharge(tenantId, callLog);
        llmCallLogMapper.insert(callLog);

        if (tenantId != null && tenantId > 0) {
            deductQuota(tenantId, totalTokens);
            syncTokenUsed(tenantId, totalTokens);
        } else {
            log.warn("llm call without tenant context, quota skipped taskType={}", request.taskType());
        }
        billingHook.afterCharge(tenantId, callLog, cost);

        return new LlmChatResponse(result.content(), providerName, result.model(),
                result.promptTokens(), result.completionTokens());
    }

    /**
     * Redis Lua 原子扣减额度，不足抛 40429（HTTP 429）。
     */
    private void deductQuota(Long tenantId, int tokens) {
        TenantQuota quota = tenantQuotaMapper.selectOne(
                new QueryWrapper<TenantQuota>().eq("tenant_id", tenantId));
        long dbRemain = quota == null ? 0L
                : quota.getTokenTotal() - (quota.getTokenUsed() == null ? 0L : quota.getTokenUsed());
        Long remain = redisTemplate.execute(DEDUCT_SCRIPT,
                List.of(TenantService.quotaRedisKey(tenantId)),
                String.valueOf(tokens), String.valueOf(dbRemain));
        if (remain == null || remain < 0) {
            throw new BizException(ErrorCode.QUOTA_EXCEEDED,
                    "tenantId=" + tenantId + " need=" + tokens);
        }
    }

    /**
     * 同步 DB 已用额度（Redis 计数为准，DB 做对账口径）。
     */
    private void syncTokenUsed(Long tenantId, int tokens) {
        TenantQuota quota = tenantQuotaMapper.selectOne(
                new QueryWrapper<TenantQuota>().eq("tenant_id", tenantId));
        if (quota != null) {
            quota.setTokenUsed((quota.getTokenUsed() == null ? 0L : quota.getTokenUsed()) + tokens);
            tenantQuotaMapper.updateById(quota);
        }
    }
}
