package com.swa.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.dto.QuotaUpdateRequest;
import com.swa.backend.dto.TenantRequest;
import com.swa.backend.entity.Tenant;
import com.swa.backend.entity.TenantQuota;
import com.swa.backend.mapper.TenantMapper;
import com.swa.backend.mapper.TenantQuotaMapper;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 租户与额度管理（仅 admin）。tenant 表不参与租户拦截，可跨租户管理。
 */
@Service
public class TenantService {

    private final TenantMapper tenantMapper;
    private final TenantQuotaMapper tenantQuotaMapper;
    private final RedisTemplate<String, String> redisTemplate;

    public TenantService(TenantMapper tenantMapper, TenantQuotaMapper tenantQuotaMapper,
                         RedisTemplate<String, String> redisTemplate) {
        this.tenantMapper = tenantMapper;
        this.tenantQuotaMapper = tenantQuotaMapper;
        this.redisTemplate = redisTemplate;
    }

    public Page<Tenant> page(int pageNo, int pageSize) {
        return tenantMapper.selectPage(new Page<>(pageNo, pageSize),
                new QueryWrapper<Tenant>().orderByDesc("id"));
    }

    /**
     * 创建租户并初始化额度行与 Redis 额度计数。
     */
    @Transactional
    public Tenant create(TenantRequest request) {
        Long count = tenantMapper.selectCount(new QueryWrapper<Tenant>().eq("name", request.name()));
        if (count != null && count > 0) {
            throw new BizException(ErrorCode.PARAM_ERROR, "租户名已存在");
        }
        Tenant tenant = new Tenant();
        tenant.setName(request.name());
        tenant.setStatus(request.status() == null ? "active" : request.status());
        tenantMapper.insert(tenant);
        // tenant 行自身的 tenant_id 回填为自身 id，保持全表 tenant_id NOT NULL
        tenant.setTenantId(tenant.getId());
        tenantMapper.updateById(tenant);

        TenantQuota quota = new TenantQuota();
        quota.setTenantId(tenant.getId());
        quota.setTokenTotal(request.tokenTotal() == null ? 100000L : request.tokenTotal());
        quota.setTokenUsed(0L);
        // 额度表插入需要租户上下文，这里显式补一次（当前登录 admin 的租户 ≠ 新租户）
        Long backup = com.swa.backend.common.TenantContext.getTenantId();
        com.swa.backend.common.TenantContext.setTenantId(tenant.getId());
        try {
            tenantQuotaMapper.insert(quota);
        } finally {
            com.swa.backend.common.TenantContext.setTenantId(backup);
        }
        redisTemplate.opsForValue().setIfAbsent(quotaRedisKey(tenant.getId()), String.valueOf(quota.getTokenTotal()));
        return tenant;
    }

    public Tenant update(Long id, TenantRequest request) {
        Tenant tenant = tenantMapper.selectById(id);
        if (tenant == null) {
            throw new BizException(ErrorCode.NOT_FOUND, "租户不存在");
        }
        if (request.name() != null) {
            tenant.setName(request.name());
        }
        if (request.status() != null) {
            tenant.setStatus(request.status());
        }
        tenantMapper.updateById(tenant);
        return tenant;
    }

    public void delete(Long id) {
        if (tenantMapper.selectById(id) == null) {
            throw new BizException(ErrorCode.NOT_FOUND, "租户不存在");
        }
        tenantMapper.deleteById(id);
    }

    /**
     * 配置租户额度：更新 DB 并重置 Redis 额度计数。
     */
    public void updateQuota(Long tenantId, QuotaUpdateRequest request) {
        if (tenantMapper.selectById(tenantId) == null) {
            throw new BizException(ErrorCode.NOT_FOUND, "租户不存在");
        }
        TenantQuota quota = tenantQuotaMapper.selectOne(
                new QueryWrapper<TenantQuota>().eq("tenant_id", tenantId));
        if (quota == null) {
            quota = new TenantQuota();
            quota.setTenantId(tenantId);
            quota.setTokenTotal(request.tokenTotal());
            quota.setTokenUsed(0L);
            Long backup = com.swa.backend.common.TenantContext.getTenantId();
            com.swa.backend.common.TenantContext.setTenantId(tenantId);
            try {
                tenantQuotaMapper.insert(quota);
            } finally {
                com.swa.backend.common.TenantContext.setTenantId(backup);
            }
        } else {
            quota.setTokenTotal(request.tokenTotal());
            Long backup = com.swa.backend.common.TenantContext.getTenantId();
            com.swa.backend.common.TenantContext.setTenantId(tenantId);
            try {
                tenantQuotaMapper.updateById(quota);
            } finally {
                com.swa.backend.common.TenantContext.setTenantId(backup);
            }
        }
        redisTemplate.opsForValue().set(quotaRedisKey(tenantId),
                String.valueOf(request.tokenTotal() - (quota.getTokenUsed() == null ? 0L : quota.getTokenUsed())));
    }

    public static String quotaRedisKey(Long tenantId) {
        return "quota:remain:" + tenantId;
    }
}
