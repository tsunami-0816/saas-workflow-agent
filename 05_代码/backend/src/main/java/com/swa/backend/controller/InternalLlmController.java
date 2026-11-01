package com.swa.backend.controller;

import com.swa.backend.common.Result;
import com.swa.backend.common.TenantContext;
import com.swa.backend.dto.LlmChatRequest;
import com.swa.backend.dto.LlmChatResponse;
import com.swa.backend.llm.LlmRouterService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 内部模型路由接口（BE-6.1）：仅 python-agent 经 X-Internal-Token 调用，无 JWT/角色。
 * 租户口径（联调待核对项，见接口文档）：调用方应传 X-Tenant-Id 头以启用额度扣减与台账归租；
 * 缺省时台账 tenantId=0 占位并跳过额度扣减（日志显式告警）。
 */
@Tag(name = "内部接口")
@RestController
@RequestMapping("/internal")
public class InternalLlmController {

    private final LlmRouterService llmRouterService;

    public InternalLlmController(LlmRouterService llmRouterService) {
        this.llmRouterService = llmRouterService;
    }

    @Operation(summary = "模型路由统一入口")
    @PostMapping("/llm/chat")
    public Result<LlmChatResponse> chat(@Valid @RequestBody LlmChatRequest request,
                                        @RequestHeader(name = "X-Tenant-Id", required = false) Long tenantId) {
        if (tenantId != null) {
            TenantContext.setTenantId(tenantId);
        }
        try {
            return Result.ok(llmRouterService.chat(request));
        } finally {
            TenantContext.clear();
        }
    }
}
