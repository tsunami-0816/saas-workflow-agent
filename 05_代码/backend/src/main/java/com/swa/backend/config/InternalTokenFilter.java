package com.swa.backend.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.common.Result;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * 内部接口过滤器：/internal/** 要求 X-Internal-Token 与配置一致（python-agent 调用模型路由层用）。
 */
@Component
public class InternalTokenFilter extends OncePerRequestFilter {

    private final String internalToken;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public InternalTokenFilter(@Value("${security.internal-token}") String internalToken) {
        this.internalToken = internalToken;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !request.getRequestURI().startsWith("/internal/");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String token = request.getHeader("X-Internal-Token");
        if (internalToken.equals(token)) {
            chain.doFilter(request, response);
            return;
        }
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.getWriter().write(objectMapper.writeValueAsString(Result.error(ErrorCode.UNAUTHORIZED)));
    }
}
