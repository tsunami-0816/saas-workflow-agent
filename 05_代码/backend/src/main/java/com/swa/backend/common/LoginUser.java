package com.swa.backend.common;

/**
 * 登录用户主体，从 JWT claim 还原：userId/tenantId/role。
 * role 取值：admin / dev / viewer。
 */
public class LoginUser {

    private Long userId;
    private Long tenantId;
    private String username;
    private String role;

    public LoginUser() {
    }

    public LoginUser(Long userId, Long tenantId, String username, String role) {
        this.userId = userId;
        this.tenantId = tenantId;
        this.username = username;
        this.role = role;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public Long getTenantId() {
        return tenantId;
    }

    public void setTenantId(Long tenantId) {
        this.tenantId = tenantId;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }
}
