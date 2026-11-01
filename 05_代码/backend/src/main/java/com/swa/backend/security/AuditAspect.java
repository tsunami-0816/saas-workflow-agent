package com.swa.backend.security;

import com.swa.backend.common.LoginUser;
import com.swa.backend.common.TenantContext;
import com.swa.backend.entity.AuditLog;
import com.swa.backend.mapper.AuditLogMapper;
import jakarta.servlet.http.HttpServletRequest;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

/**
 * 审计切面：@Audit 标注的写操作成功返回后落 audit_log（BE-1.5）。
 */
@Aspect
@Component
@Order(2)
public class AuditAspect {

    private static final Logger log = LoggerFactory.getLogger(AuditAspect.class);

    private final AuditLogMapper auditLogMapper;

    public AuditAspect(AuditLogMapper auditLogMapper) {
        this.auditLogMapper = auditLogMapper;
    }

    @Around("@annotation(audit)")
    public Object around(ProceedingJoinPoint pjp, Audit audit) throws Throwable {
        Object result = pjp.proceed();
        try {
            LoginUser user = TenantContext.getLoginUser();
            AuditLog record = new AuditLog();
            record.setTenantId(user != null ? user.getTenantId() : TenantContext.getTenantId());
            record.setUserId(user != null ? user.getUserId() : null);
            record.setAction(audit.action());
            record.setTarget(pjp.getSignature().toShortString());
            record.setDetail(summarizeArgs(pjp.getArgs()));
            record.setIp(currentIp());
            auditLogMapper.insert(record);
        } catch (Exception e) {
            // 审计失败不阻断主流程
            log.warn("audit log write failed: {}", e.getMessage());
        }
        return result;
    }

    private String summarizeArgs(Object[] args) {
        if (args == null || args.length == 0) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        for (Object arg : args) {
            if (arg == null) {
                continue;
            }
            String s = arg.toString();
            // detail 列长度有限，截断；且绝不记录密码字段（入参 DTO 不打印 password）
            if (s.length() > 200) {
                s = s.substring(0, 200);
            }
            sb.append(s).append(';');
        }
        return sb.toString();
    }

    private String currentIp() {
        try {
            ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs == null) {
                return "";
            }
            HttpServletRequest request = attrs.getRequest();
            String ip = request.getHeader("X-Forwarded-For");
            return ip != null ? ip.split(",")[0].trim() : request.getRemoteAddr();
        } catch (Exception e) {
            return "";
        }
    }
}
