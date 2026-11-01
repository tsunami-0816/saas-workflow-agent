package com.swa.backend.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.Result;
import com.swa.backend.dto.UserCreateRequest;
import com.swa.backend.dto.UserUpdateRequest;
import com.swa.backend.entity.User;
import com.swa.backend.security.Audit;
import com.swa.backend.security.RequireRole;
import com.swa.backend.service.UserService;
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
 * 用户管理接口（仅 admin）。
 */
@Tag(name = "用户管理")
@RestController
@RequestMapping("/api/v1/users")
@RequireRole("admin")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @Operation(summary = "用户分页列表")
    @GetMapping
    public Result<Page<User>> page(@RequestParam(defaultValue = "1") int pageNo,
                                   @RequestParam(defaultValue = "20") int pageSize,
                                   @RequestParam(required = false) String username) {
        Page<User> page = userService.page(pageNo, pageSize, username);
        page.getRecords().forEach(u -> u.setPasswordHash(null));
        return Result.ok(page);
    }

    @Audit(action = "user.create")
    @Operation(summary = "创建用户")
    @PostMapping
    public Result<User> create(@Valid @RequestBody UserCreateRequest request) {
        return Result.ok(userService.create(request));
    }

    @Audit(action = "user.update")
    @Operation(summary = "更新用户")
    @PutMapping("/{id}")
    public Result<User> update(@PathVariable Long id, @Valid @RequestBody UserUpdateRequest request) {
        return Result.ok(userService.update(id, request));
    }

    @Audit(action = "user.delete")
    @Operation(summary = "删除用户")
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        userService.delete(id);
        return Result.ok();
    }
}
