package com.swa.backend.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.Result;
import com.swa.backend.dto.CredentialRequest;
import com.swa.backend.entity.ConnectorCredential;
import com.swa.backend.security.Audit;
import com.swa.backend.security.RequireRole;
import com.swa.backend.service.CredentialService;
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
 * 连接器凭据管理接口（BE-7.2，仅 admin）。返回一律脱敏。
 */
@Tag(name = "连接器凭据")
@RestController
@RequestMapping("/api/v1/credentials")
@RequireRole("admin")
public class CredentialController {

    private final CredentialService credentialService;

    public CredentialController(CredentialService credentialService) {
        this.credentialService = credentialService;
    }

    @Operation(summary = "凭据分页列表")
    @GetMapping
    public Result<Page<ConnectorCredential>> page(@RequestParam(defaultValue = "1") int pageNo,
                                                  @RequestParam(defaultValue = "20") int pageSize) {
        return Result.ok(credentialService.page(pageNo, pageSize));
    }

    @Operation(summary = "凭据详情（脱敏）")
    @GetMapping("/{id}")
    public Result<ConnectorCredential> get(@PathVariable Long id) {
        return Result.ok(credentialService.get(id));
    }

    @Audit(action = "credential.create")
    @Operation(summary = "创建凭据（configJson 服务端 AES 加密入库）")
    @PostMapping
    public Result<ConnectorCredential> create(@Valid @RequestBody CredentialRequest request) {
        return Result.ok(credentialService.create(request));
    }

    @Audit(action = "credential.update")
    @Operation(summary = "更新凭据")
    @PutMapping("/{id}")
    public Result<ConnectorCredential> update(@PathVariable Long id,
                                              @Valid @RequestBody CredentialRequest request) {
        return Result.ok(credentialService.update(id, request));
    }

    @Audit(action = "credential.delete")
    @Operation(summary = "删除凭据")
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        credentialService.delete(id);
        return Result.ok();
    }
}
