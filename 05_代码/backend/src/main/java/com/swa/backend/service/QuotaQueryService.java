package com.swa.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.common.TenantContext;
import com.swa.backend.entity.AuditLog;
import com.swa.backend.entity.LlmCallLog;
import com.swa.backend.entity.TenantQuota;
import com.swa.backend.mapper.AuditLogMapper;
import com.swa.backend.mapper.LlmCallLogMapper;
import com.swa.backend.mapper.TenantQuotaMapper;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 额度/计量/审计查询（BE-2.4 扩展，M4 台账可查）。
 */
@Service
public class QuotaQueryService {

    private final TenantQuotaMapper tenantQuotaMapper;
    private final LlmCallLogMapper llmCallLogMapper;
    private final AuditLogMapper auditLogMapper;
    private final RedisTemplate<String, String> redisTemplate;

    public QuotaQueryService(TenantQuotaMapper tenantQuotaMapper, LlmCallLogMapper llmCallLogMapper,
                             AuditLogMapper auditLogMapper, RedisTemplate<String, String> redisTemplate) {
        this.tenantQuotaMapper = tenantQuotaMapper;
        this.llmCallLogMapper = llmCallLogMapper;
        this.auditLogMapper = auditLogMapper;
        this.redisTemplate = redisTemplate;
    }

    /**
     * 当前租户额度：DB 口径 + Redis 实时剩余。
     */
    public Map<String, Object> myQuota() {
        Long tenantId = TenantContext.getTenantId();
        TenantQuota quota = tenantQuotaMapper.selectOne(
                new QueryWrapper<TenantQuota>().eq("tenant_id", tenantId));
        if (quota == null) {
            throw new BizException(ErrorCode.NOT_FOUND, "租户额度未配置");
        }
        String remain = redisTemplate.opsForValue().get(TenantService.quotaRedisKey(tenantId));
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("tenantId", tenantId);
        result.put("tokenTotal", quota.getTokenTotal());
        result.put("tokenUsed", quota.getTokenUsed());
        result.put("tokenRemainRedis", remain == null ? null : Long.parseLong(remain));
        return result;
    }

    /**
     * 本租户 LLM 调用台账分页（M4）。
     */
    public Page<LlmCallLog> llmCalls(int pageNo, int pageSize) {
        return llmCallLogMapper.selectPage(new Page<>(pageNo, pageSize),
                new QueryWrapper<LlmCallLog>().orderByDesc("id"));
    }

    /**
     * 本租户审计日志分页（仅 admin，由控制器层角色注解保证）。
     */
    public Page<AuditLog> auditLogs(int pageNo, int pageSize) {
        return auditLogMapper.selectPage(new Page<>(pageNo, pageSize),
                new QueryWrapper<AuditLog>().orderByDesc("id"));
    }
}
