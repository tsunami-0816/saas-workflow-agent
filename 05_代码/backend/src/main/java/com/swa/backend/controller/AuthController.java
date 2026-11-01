package com.swa.backend.controller;

import com.swa.backend.common.LoginUser;
import com.swa.backend.common.Result;
import com.swa.backend.common.TenantContext;
import com.swa.backend.dto.LoginRequest;
import com.swa.backend.dto.LoginResponse;
import com.swa.backend.service.AuthService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 认证接口（L1）。
 */
@Tag(name = "认证")
@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    /**
     * 登录签发 JWT。tenantId 传参一律忽略。
     */
    @Operation(summary = "登录签发 JWT")
    @PostMapping("/login")
    public Result<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        return Result.ok(authService.login(request));
    }

    /**
     * 当前登录用户信息。
     */
    @Operation(summary = "当前登录用户")
    @GetMapping("/me")
    public Result<LoginUser> me() {
        return Result.ok(TenantContext.getLoginUser());
    }
}
