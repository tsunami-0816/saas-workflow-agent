package com.swa.backend.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.Result;
import com.swa.backend.dto.QuotaUpdateRequest;
import com.swa.backend.dto.TenantRequest;
import com.swa.backend.entity.Tenant;
import com.swa.backend.security.Audit;
import com.swa.backend.security.RequireRole;
import com.swa.backend.service.TenantService;
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
 * 租户与额度配置接口（仅 admin）。
 */
@Tag(name = "租户管理")
@RestController
@RequestMapping("/api/v1/tenants")
@RequireRole("admin")
public class TenantController {

    private final TenantService tenantService;

    public TenantController(TenantService tenantService) {
        this.tenantService = tenantService;
    }

    @Operation(summary = "租户分页列表")
    @GetMapping
    public Result<Page<Tenant>> page(@RequestParam(defaultValue = "1") int pageNo,
                                     @RequestParam(defaultValue = "20") int pageSize) {
        return Result.ok(tenantService.page(pageNo, pageSize));
    }

    @Audit(action = "tenant.create")
    @Operation(summary = "创建租户")
    @PostMapping
    public Result<Tenant> create(@Valid @RequestBody TenantRequest request) {
        return Result.ok(tenantService.create(request));
    }

    @Audit(action = "tenant.update")
    @Operation(summary = "更新租户")
    @PutMapping("/{id}")
    public Result<Tenant> update(@PathVariable Long id, @Valid @RequestBody TenantRequest request) {
        return Result.ok(tenantService.update(id, request));
    }

    @Audit(action = "tenant.delete")
    @Operation(summary = "删除租户")
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        tenantService.delete(id);
        return Result.ok();
    }

    @Audit(action = "tenant.quota.update")
    @Operation(summary = "配置租户额度")
    @PutMapping("/{id}/quota")
    public Result<Void> updateQuota(@PathVariable Long id, @Valid @RequestBody QuotaUpdateRequest request) {
        tenantService.updateQuota(id, request);
        return Result.ok();
    }
}
