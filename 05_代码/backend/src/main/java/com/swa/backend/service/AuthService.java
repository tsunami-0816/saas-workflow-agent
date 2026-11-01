package com.swa.backend.service;

import cn.hutool.crypto.digest.BCrypt;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.common.LoginUser;
import com.swa.backend.dto.LoginRequest;
import com.swa.backend.dto.LoginResponse;
import com.swa.backend.entity.User;
import com.swa.backend.mapper.UserMapper;
import com.swa.backend.security.JwtUtil;
import org.springframework.stereotype.Service;

/**
 * 认证服务：账号密码校验 → 签发 JWT（L1）。
 */
@Service
public class AuthService {

    private final UserMapper userMapper;
    private final JwtUtil jwtUtil;

    public AuthService(UserMapper userMapper, JwtUtil jwtUtil) {
        this.userMapper = userMapper;
        this.jwtUtil = jwtUtil;
    }

    /**
     * 登录。
     *
     * @param request 账号密码（tenantId 传参一律忽略）
     * @return token 与用户信息
     */
    public LoginResponse login(LoginRequest request) {
        User user = userMapper.selectByUsernameIgnoreTenant(request.username());
        if (user == null || !BCrypt.checkpw(request.password(), user.getPasswordHash())) {
            throw new BizException(ErrorCode.UNAUTHORIZED, "账号或密码错误");
        }
        if (!"active".equals(user.getStatus())) {
            throw new BizException(ErrorCode.UNAUTHORIZED, "账号已停用");
        }
        LoginUser loginUser = new LoginUser(user.getId(), user.getTenantId(), user.getUsername(), user.getRole());
        String token = jwtUtil.sign(loginUser);
        return new LoginResponse(token, user.getId(), user.getTenantId(), user.getUsername(), user.getRole());
    }
}
