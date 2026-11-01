package com.swa.backend.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.Result;
import com.swa.backend.dto.NlDraftRequest;
import com.swa.backend.dto.VersionSaveRequest;
import com.swa.backend.dto.WorkflowCreateRequest;
import com.swa.backend.dto.WorkflowUpdateRequest;
import com.swa.backend.entity.Workflow;
import com.swa.backend.entity.WorkflowVersion;
import com.swa.backend.nl.NlFlowService;
import com.swa.backend.security.Audit;
import com.swa.backend.security.RequireRole;
import com.swa.backend.service.WorkflowService;
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
 * 流程定义与版本管理接口（BE-3/BE-8）。
 */
@Tag(name = "流程管理")
@RestController
@RequestMapping("/api/v1/workflows")
public class WorkflowController {

    private final WorkflowService workflowService;
    private final NlFlowService nlFlowService;

    public WorkflowController(WorkflowService workflowService, NlFlowService nlFlowService) {
        this.workflowService = workflowService;
        this.nlFlowService = nlFlowService;
    }

    @Operation(summary = "流程分页列表")
    @GetMapping
    @RequireRole({"admin", "dev", "viewer"})
    public Result<Page<Workflow>> page(@RequestParam(defaultValue = "1") int pageNo,
                                       @RequestParam(defaultValue = "20") int pageSize,
                                       @RequestParam(required = false) String name) {
        return Result.ok(workflowService.pageWorkflows(pageNo, pageSize, name));
    }

    @Operation(summary = "流程详情")
    @GetMapping("/{id}")
    @RequireRole({"admin", "dev", "viewer"})
    public Result<Workflow> get(@PathVariable Long id) {
        return Result.ok(workflowService.getWorkflow(id));
    }

    @Audit(action = "workflow.create")
    @Operation(summary = "创建流程")
    @PostMapping
    @RequireRole({"admin", "dev"})
    public Result<Workflow> create(@Valid @RequestBody WorkflowCreateRequest request) {
        return Result.ok(workflowService.createWorkflow(request));
    }

    @Audit(action = "workflow.update")
    @Operation(summary = "更新流程")
    @PutMapping("/{id}")
    @RequireRole({"admin", "dev"})
    public Result<Workflow> update(@PathVariable Long id, @Valid @RequestBody WorkflowUpdateRequest request) {
        return Result.ok(workflowService.updateWorkflow(id, request));
    }

    @Audit(action = "workflow.delete")
    @Operation(summary = "删除流程")
    @DeleteMapping("/{id}")
    @RequireRole({"admin", "dev"})
    public Result<Void> delete(@PathVariable Long id) {
        workflowService.deleteWorkflow(id);
        return Result.ok();
    }

    @Operation(summary = "版本列表")
    @GetMapping("/{id}/versions")
    @RequireRole({"admin", "dev", "viewer"})
    public Result<Page<WorkflowVersion>> versions(@PathVariable Long id,
                                                  @RequestParam(defaultValue = "1") int pageNo,
                                                  @RequestParam(defaultValue = "20") int pageSize) {
        return Result.ok(workflowService.pageVersions(id, pageNo, pageSize));
    }

    @Audit(action = "workflow.version.save")
    @Operation(summary = "保存新版本（DSL Schema 校验）")
    @PostMapping("/{id}/versions")
    @RequireRole({"admin", "dev"})
    public Result<WorkflowVersion> saveVersion(@PathVariable Long id,
                                               @Valid @RequestBody VersionSaveRequest request) {
        return Result.ok(workflowService.saveVersion(id, request.dslJson()));
    }

    @Operation(summary = "版本详情")
    @GetMapping("/versions/{versionId}")
    @RequireRole({"admin", "dev", "viewer"})
    public Result<WorkflowVersion> getVersion(@PathVariable Long versionId) {
        return Result.ok(workflowService.getVersion(versionId));
    }

    @Audit(action = "workflow.version.publish")
    @Operation(summary = "发布版本")
    @PutMapping("/versions/{versionId}/publish")
    @RequireRole({"admin", "dev"})
    public Result<WorkflowVersion> publish(@PathVariable Long versionId) {
        return Result.ok(workflowService.publish(versionId));
    }

    @Audit(action = "workflow.version.disable")
    @Operation(summary = "禁用版本")
    @PutMapping("/versions/{versionId}/disable")
    @RequireRole({"admin", "dev"})
    public Result<WorkflowVersion> disable(@PathVariable Long versionId) {
        return Result.ok(workflowService.disable(versionId));
    }

    @Audit(action = "workflow.nl-draft")
    @Operation(summary = "NL→流程草稿（L7）")
    @PostMapping("/nl-draft")
    @RequireRole({"admin", "dev"})
    public Result<WorkflowVersion> nlDraft(@Valid @RequestBody NlDraftRequest request) {
        return Result.ok(nlFlowService.generateDraft(request));
    }
}
