package com.swa.backend.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.LoginUser;
import com.swa.backend.common.Result;
import com.swa.backend.common.TenantContext;
import com.swa.backend.dto.ExecutionCreateRequest;
import com.swa.backend.engine.SseEmitterManager;
import com.swa.backend.entity.Execution;
import com.swa.backend.entity.NodeExecution;
import com.swa.backend.security.Audit;
import com.swa.backend.security.RequireRole;
import com.swa.backend.service.ExecutionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;

/**
 * 执行管理接口（BE-4.2/BE-4.9/BE-4.11/BE-5）。
 */
@Tag(name = "执行管理")
@RestController
@RequestMapping("/api/v1/executions")
public class ExecutionController {

    private final ExecutionService executionService;
    private final SseEmitterManager sseEmitterManager;

    public ExecutionController(ExecutionService executionService, SseEmitterManager sseEmitterManager) {
        this.executionService = executionService;
        this.sseEmitterManager = sseEmitterManager;
    }

    @Audit(action = "execution.create")
    @Operation(summary = "创建执行（幂等：同 user+version+clientReqId 只建 1 个实例）")
    @PostMapping
    @RequireRole({"admin", "dev"})
    public Result<Execution> create(@Valid @RequestBody ExecutionCreateRequest request) {
        LoginUser user = TenantContext.getLoginUser();
        return Result.ok(executionService.create(request, user.getUserId()));
    }

    @Operation(summary = "执行分页列表")
    @GetMapping
    @RequireRole({"admin", "dev", "viewer"})
    public Result<Page<Execution>> page(@RequestParam(defaultValue = "1") int pageNo,
                                        @RequestParam(defaultValue = "20") int pageSize,
                                        @RequestParam(required = false) String status) {
        return Result.ok(executionService.page(pageNo, pageSize, status));
    }

    @Operation(summary = "执行详情")
    @GetMapping("/{id}")
    @RequireRole({"admin", "dev", "viewer"})
    public Result<Execution> get(@PathVariable Long id) {
        return Result.ok(executionService.get(id));
    }

    @Operation(summary = "节点快照（SSE 断线续订先拉快照）")
    @GetMapping("/{id}/nodes")
    @RequireRole({"admin", "dev", "viewer"})
    public Result<List<NodeExecution>> nodes(@PathVariable Long id) {
        return Result.ok(executionService.nodes(id));
    }

    @Operation(summary = "执行实时事件流（SSE：node/execution 事件）")
    @GetMapping(path = "/{id}/events", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @RequireRole({"admin", "dev", "viewer"})
    public SseEmitter events(@PathVariable Long id) {
        executionService.get(id); // 存在性 + 租户隔离校验
        return sseEmitterManager.subscribe(id);
    }

    @Audit(action = "execution.replay")
    @Operation(summary = "回放：按原参数重新触发，产生新实例")
    @PostMapping("/{id}/replay")
    @RequireRole({"admin", "dev"})
    public Result<Execution> replay(@PathVariable Long id) {
        LoginUser user = TenantContext.getLoginUser();
        return Result.ok(executionService.replay(id, user.getUserId()));
    }
}
