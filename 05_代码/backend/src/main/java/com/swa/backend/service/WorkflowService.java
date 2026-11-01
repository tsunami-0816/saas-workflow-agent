package com.swa.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.common.TenantContext;
import com.swa.backend.dto.WorkflowCreateRequest;
import com.swa.backend.dto.WorkflowUpdateRequest;
import com.swa.backend.engine.dsl.DslValidator;
import com.swa.backend.entity.Workflow;
import com.swa.backend.entity.WorkflowVersion;
import com.swa.backend.mapper.WorkflowMapper;
import com.swa.backend.mapper.WorkflowVersionMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 流程定义与版本管理（BE-3）。版本三态：draft/published/disabled。
 */
@Service
public class WorkflowService {

    private final WorkflowMapper workflowMapper;
    private final WorkflowVersionMapper versionMapper;
    private final DslValidator dslValidator;

    public WorkflowService(WorkflowMapper workflowMapper, WorkflowVersionMapper versionMapper,
                           DslValidator dslValidator) {
        this.workflowMapper = workflowMapper;
        this.versionMapper = versionMapper;
        this.dslValidator = dslValidator;
    }

    public Page<Workflow> pageWorkflows(int pageNo, int pageSize, String name) {
        QueryWrapper<Workflow> wrapper = new QueryWrapper<>();
        if (name != null && !name.isBlank()) {
            wrapper.like("name", name);
        }
        wrapper.orderByDesc("id");
        return workflowMapper.selectPage(new Page<>(pageNo, pageSize), wrapper);
    }

    public Workflow getWorkflow(Long id) {
        Workflow workflow = workflowMapper.selectById(id);
        if (workflow == null) {
            throw new BizException(ErrorCode.WORKFLOW_NOT_FOUND);
        }
        return workflow;
    }

    public Workflow createWorkflow(WorkflowCreateRequest request) {
        Workflow workflow = new Workflow();
        workflow.setName(request.name());
        workflow.setDescription(request.description());
        workflowMapper.insert(workflow);
        // BUG-001 修复：insert 后 MyBatis-Plus 多租户插件写库了 tenant_id 但未回填到实体，
        // 从 TenantContext 补到返回对象，避免创建响应 tenantId=null
        workflow.setTenantId(TenantContext.getTenantId());
        return workflow;
    }

    public Workflow updateWorkflow(Long id, WorkflowUpdateRequest request) {
        Workflow workflow = getWorkflow(id);
        if (request.name() != null) {
            workflow.setName(request.name());
        }
        if (request.description() != null) {
            workflow.setDescription(request.description());
        }
        workflowMapper.updateById(workflow);
        return workflow;
    }

    public void deleteWorkflow(Long id) {
        getWorkflow(id);
        workflowMapper.deleteById(id);
    }

    /**
     * 保存新版本：DSL Schema 校验通过后落库，版本号自增，初始 status=draft。
     *
     * @return 新建的版本
     */
    @Transactional
    public WorkflowVersion saveVersion(Long workflowId, String dslJson) {
        getWorkflow(workflowId);
        // 校验失败抛 2xxxx 错误码
        dslValidator.validate(dslJson);
        WorkflowVersion latest = versionMapper.selectOne(new QueryWrapper<WorkflowVersion>()
                .eq("workflow_id", workflowId).orderByDesc("version_no").last("limit 1"));
        int nextNo = latest == null ? 1 : latest.getVersionNo() + 1;
        WorkflowVersion version = new WorkflowVersion();
        version.setWorkflowId(workflowId);
        version.setVersionNo(nextNo);
        version.setDslJson(dslJson);
        version.setStatus("draft");
        versionMapper.insert(version);
        return version;
    }

    public Page<WorkflowVersion> pageVersions(Long workflowId, int pageNo, int pageSize) {
        getWorkflow(workflowId);
        return versionMapper.selectPage(new Page<>(pageNo, pageSize),
                new QueryWrapper<WorkflowVersion>().eq("workflow_id", workflowId).orderByDesc("version_no"));
    }

    public WorkflowVersion getVersion(Long versionId) {
        WorkflowVersion version = versionMapper.selectById(versionId);
        if (version == null) {
            throw new BizException(ErrorCode.VERSION_NOT_FOUND);
        }
        return version;
    }

    /**
     * 发布版本：draft/disabled → published。
     */
    public WorkflowVersion publish(Long versionId) {
        WorkflowVersion version = getVersion(versionId);
        if ("published".equals(version.getStatus())) {
            return version;
        }
        if (!"draft".equals(version.getStatus()) && !"disabled".equals(version.getStatus())) {
            throw new BizException(ErrorCode.VERSION_STATUS_ILLEGAL, version.getStatus());
        }
        version.setStatus("published");
        versionMapper.updateById(version);
        return version;
    }

    /**
     * 禁用版本：published → disabled（禁用后不可执行）。
     */
    public WorkflowVersion disable(Long versionId) {
        WorkflowVersion version = getVersion(versionId);
        if (!"published".equals(version.getStatus())) {
            throw new BizException(ErrorCode.VERSION_STATUS_ILLEGAL, "仅 published 可禁用, 当前=" + version.getStatus());
        }
        version.setStatus("disabled");
        versionMapper.updateById(version);
        return version;
    }
}
