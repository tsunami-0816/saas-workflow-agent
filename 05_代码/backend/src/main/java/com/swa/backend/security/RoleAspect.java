package com.swa.backend.security;

import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.common.LoginUser;
import com.swa.backend.common.TenantContext;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.util.ClassUtils;

import java.util.Arrays;

/**
 * @RequireRole AOP 实现：从 TenantContext 取登录用户角色，命中放行，否则抛 10403。
 * 同时支持方法级与类级注解（方法级优先于类级）。
 */
@Aspect
@Component
@Order(1)
public class RoleAspect {

    @Before("@annotation(com.swa.backend.security.RequireRole) || @within(com.swa.backend.security.RequireRole)")
    public void check(JoinPoint joinPoint) {
        RequireRole requireRole = resolve(joinPoint);
        if (requireRole == null) {
            return;
        }
        LoginUser user = TenantContext.getLoginUser();
        if (user == null) {
            throw new BizException(ErrorCode.UNAUTHORIZED);
        }
        boolean ok = Arrays.asList(requireRole.value()).contains(user.getRole());
        if (!ok) {
            throw new BizException(ErrorCode.FORBIDDEN);
        }
    }

    private RequireRole resolve(JoinPoint joinPoint) {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        RequireRole methodLevel = signature.getMethod().getAnnotation(RequireRole.class);
        if (methodLevel != null) {
            return methodLevel;
        }
        return ClassUtils.getUserClass(joinPoint.getTarget().getClass()).getAnnotation(RequireRole.class);
    }
}
