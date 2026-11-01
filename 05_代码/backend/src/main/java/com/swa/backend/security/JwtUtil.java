package com.swa.backend.security;

import com.swa.backend.common.LoginUser;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

/**
 * JWT 工具：签发/解析。claim 含 userId/tenantId/role。
 * 密钥走环境变量 JWT_SECRET（HS256，要求 ≥32 字节）。
 */
@Component
public class JwtUtil {

    private final SecretKey key;
    private final long expireMillis;

    public JwtUtil(@Value("${security.jwt.secret}") String secret,
                   @Value("${security.jwt.expire-hours:12}") long expireHours) {
        byte[] raw = secret.getBytes(StandardCharsets.UTF_8);
        if (raw.length < 32) {
            throw new IllegalStateException("JWT_SECRET 长度不足 32 字节");
        }
        this.key = Keys.hmacShaKeyFor(raw);
        this.expireMillis = expireHours * 3600_000L;
    }

    /**
     * 签发 token。
     *
     * @param user 登录用户主体（id/tenantId/username/role）
     * @return JWT 字符串
     */
    public String sign(LoginUser user) {
        Date now = new Date();
        return Jwts.builder()
                .subject(String.valueOf(user.getUserId()))
                .claim("userId", user.getUserId())
                .claim("tenantId", user.getTenantId())
                .claim("username", user.getUsername())
                .claim("role", user.getRole())
                .issuedAt(now)
                .expiration(new Date(now.getTime() + expireMillis))
                .signWith(key)
                .compact();
    }

    /**
     * 解析并校验 token，非法/过期抛异常（由过滤器统一转 401）。
     *
     * @param token JWT 字符串
     * @return 登录用户主体
     */
    public LoginUser parse(String token) {
        Claims claims = Jwts.parser().verifyWith(key).build()
                .parseSignedClaims(token).getPayload();
        LoginUser user = new LoginUser();
        user.setUserId(claims.get("userId", Long.class));
        user.setTenantId(claims.get("tenantId", Long.class));
        user.setUsername(claims.get("username", String.class));
        user.setRole(claims.get("role", String.class));
        return user;
    }
}
