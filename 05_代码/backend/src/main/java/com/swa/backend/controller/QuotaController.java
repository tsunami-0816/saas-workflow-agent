package com.swa.backend.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.Result;
import com.swa.backend.entity.AuditLog;
import com.swa.backend.entity.LlmCallLog;
import com.swa.backend.security.RequireRole;
import com.swa.backend.service.QuotaQueryService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 额度/计量/审计查询接口（M4）。
 * 额度与调用台账：三角色可查；审计日志：仅 admin。
 */
@Tag(name = "额度与计量")
@RestController
@RequestMapping("/api/v1/quota")
public class QuotaController {

    private final QuotaQueryService quotaQueryService;

    public QuotaController(QuotaQueryService quotaQueryService) {
        this.quotaQueryService = quotaQueryService;
    }

    @Operation(summary = "当前租户额度（DB + Redis 实时剩余）")
    @GetMapping
    @RequireRole({"admin", "dev", "viewer"})
    public Result<Map<String, Object>> myQuota() {
        return Result.ok(quotaQueryService.myQuota());
    }

    @Operation(summary = "LLM 调用台账分页")
    @GetMapping("/llm-calls")
    @RequireRole({"admin", "dev", "viewer"})
    public Result<Page<LlmCallLog>> llmCalls(@RequestParam(defaultValue = "1") int pageNo,
                                             @RequestParam(defaultValue = "20") int pageSize) {
        return Result.ok(quotaQueryService.llmCalls(pageNo, pageSize));
    }

    @Operation(summary = "审计日志分页（仅 admin）")
    @GetMapping("/audit-logs")
    @RequireRole("admin")
    public Result<Page<AuditLog>> auditLogs(@RequestParam(defaultValue = "1") int pageNo,
                                            @RequestParam(defaultValue = "20") int pageSize) {
        return Result.ok(quotaQueryService.auditLogs(pageNo, pageSize));
    }
}
