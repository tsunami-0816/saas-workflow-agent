package com.swa.backend.config;

import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.BlockAttackInnerInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.TenantLineInnerInterceptor;
import com.swa.backend.common.TenantContext;
import net.sf.jsqlparser.expression.Expression;
import net.sf.jsqlparser.expression.LongValue;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Set;

/**
 * MyBatis-Plus 配置：租户拦截器 + 分页插件 + 防全表更新。
 * 租户规则：除 ignoreTables 外，全表自动注入/过滤 tenant_id（值取 TenantContext，即 JWT claim）。
 * SQL 红线：禁止 MySQL 专属方言，分页一律走本分页插件。
 */
@Configuration
public class MybatisPlusConfig {

    /** 不参与租户过滤的表：tenant 为系统表，由 admin 跨租户管理。 */
    private static final Set<String> IGNORE_TABLES = Set.of("tenant");

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        TenantLineInnerInterceptor tenantInterceptor = new TenantLineInnerInterceptor(new com.baomidou.mybatisplus.extension.plugins.handler.TenantLineHandler() {
            @Override
            public Expression getTenantId() {
                Long tenantId = TenantContext.getTenantId();
                // 后台线程（sweeper 启动收敛等）无租户上下文时给 0，仅匹配不到数据，绝不越权
                return new LongValue(tenantId == null ? 0L : tenantId);
            }

            @Override
            public String getTenantIdColumn() {
                return "tenant_id";
            }

            @Override
            public boolean ignoreTable(String tableName) {
                return IGNORE_TABLES.contains(tableName);
            }

            @Override
            public boolean ignoreInsert(java.util.List<net.sf.jsqlparser.schema.Column> columns, String tenantIdColumn) {
                // insert 语句显式给了 tenant_id 时不再强制注入
                return columns.stream().anyMatch(c -> tenantIdColumn.equalsIgnoreCase(c.getColumnName()));
            }
        });
        interceptor.addInnerInterceptor(tenantInterceptor);
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor());
        interceptor.addInnerInterceptor(new BlockAttackInnerInterceptor());
        return interceptor;
    }
}
