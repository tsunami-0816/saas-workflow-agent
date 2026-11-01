package com.swa.backend.service;

import cn.hutool.crypto.digest.BCrypt;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.common.TenantContext;
import com.swa.backend.dto.UserCreateRequest;
import com.swa.backend.dto.UserUpdateRequest;
import com.swa.backend.entity.User;
import com.swa.backend.mapper.UserMapper;
import org.springframework.stereotype.Service;

/**
 * 用户管理（仅 admin）：本租户内用户 CRUD。
 */
@Service
public class UserService {

    private final UserMapper userMapper;

    public UserService(UserMapper userMapper) {
        this.userMapper = userMapper;
    }

    /**
     * 分页查询本租户用户。
     */
    public Page<User> page(int pageNo, int pageSize, String username) {
        QueryWrapper<User> wrapper = new QueryWrapper<>();
        if (username != null && !username.isBlank()) {
            wrapper.like("username", username);
        }
        wrapper.orderByDesc("id");
        return userMapper.selectPage(new Page<>(pageNo, pageSize), wrapper);
    }

    /**
     * 创建用户：租户取 JWT claim，密码 BCrypt 加密入库。
     */
    public User create(UserCreateRequest request) {
        Long tenantId = TenantContext.getTenantId();
        Long count = userMapper.selectCount(new QueryWrapper<User>().eq("username", request.username()));
        if (count != null && count > 0) {
            throw new BizException(ErrorCode.PARAM_ERROR, "用户名已存在");
        }
        User user = new User();
        user.setTenantId(tenantId);
        user.setUsername(request.username());
        user.setPasswordHash(BCrypt.hashpw(request.password()));
        user.setDisplayName(request.displayName());
        user.setRole(request.role());
        user.setStatus("active");
        userMapper.insert(user);
        user.setPasswordHash(null);
        return user;
    }

    /**
     * 更新用户（displayName/role/status/password 可选）。
     */
    public User update(Long id, UserUpdateRequest request) {
        User user = userMapper.selectById(id);
        if (user == null) {
            throw new BizException(ErrorCode.NOT_FOUND, "用户不存在");
        }
        if (request.displayName() != null) {
            user.setDisplayName(request.displayName());
        }
        if (request.role() != null) {
            user.setRole(request.role());
        }
        if (request.status() != null) {
            user.setStatus(request.status());
        }
        if (request.password() != null && !request.password().isBlank()) {
            user.setPasswordHash(BCrypt.hashpw(request.password()));
        }
        userMapper.updateById(user);
        user.setPasswordHash(null);
        return user;
    }

    /**
     * 逻辑删除用户。不允许删除自己。
     */
    public void delete(Long id) {
        if (id.equals(TenantContext.getLoginUser().getUserId())) {
            throw new BizException(ErrorCode.PARAM_ERROR, "不能删除当前登录账号");
        }
        if (userMapper.selectById(id) == null) {
            throw new BizException(ErrorCode.NOT_FOUND, "用户不存在");
        }
        userMapper.deleteById(id);
    }
}
