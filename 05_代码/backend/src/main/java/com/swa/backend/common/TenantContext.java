package com.swa.backend.common;

/**
 * 租户上下文（ThreadLocal）。租户 id 一律以 JWT claim 为准，
 * 由 JwtAuthFilter 写入；Worker/MQTT 等后台线程由引擎按执行记录显式 set。
 * 注意：用完必须 clear()，防止线程池串租户。
 */
public final class TenantContext {

    private static final ThreadLocal<Long> TENANT = new ThreadLocal<>();
    private static final ThreadLocal<LoginUser> USER = new ThreadLocal<>();

    private TenantContext() {
    }

    public static void setTenantId(Long tenantId) {
        TENANT.set(tenantId);
    }

    public static Long getTenantId() {
        return TENANT.get();
    }

    public static void setLoginUser(LoginUser user) {
        USER.set(user);
        if (user != null) {
            TENANT.set(user.getTenantId());
        }
    }

    public static LoginUser getLoginUser() {
        return USER.get();
    }

    public static void clear() {
        TENANT.remove();
        USER.remove();
    }
}
