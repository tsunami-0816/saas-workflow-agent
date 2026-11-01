package com.swa.backend.mapper;

import com.baomidou.mybatisplus.annotation.InterceptorIgnore;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.swa.backend.entity.Execution;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.io.Serializable;
import java.util.Collection;
import java.util.List;

/**
 * Execution Mapper，继承 MyBatis-Plus BaseMapper。
 */
@Mapper
public interface ExecutionMapper  extends BaseMapper<Execution> {

    /**
     * 按 id 查询并忽略租户拦截：MQ Worker 消费消息时仅有 executionId，租户上下文由引擎恢复。
     * 注意：@InterceptorIgnore 必须标注在真实执行的 SQL 方法上（default 方法桥接不生效）。
     */
    @InterceptorIgnore(tenantLine = "true")
    @Select("SELECT id, tenant_id, version_id, user_id, status, trigger_type, trigger_payload, fail_reason, "
            + "started_at, ended_at, deleted, created_at, updated_at FROM execution WHERE id = #{id} AND deleted = 0")
    Execution selectByIdIgnoreTenant(Serializable id);

    /**
     * 按状态集合跨租户查询：sweeper 启动收敛 RUNNING/WAITING 实例用。
     */
    @InterceptorIgnore(tenantLine = "true")
    @Select("<script>SELECT id, tenant_id, version_id, user_id, status, trigger_type, trigger_payload, fail_reason, "
            + "started_at, ended_at, deleted, created_at, updated_at FROM execution WHERE deleted = 0 AND status IN "
            + "<foreach collection='statuses' item='s' open='(' separator=',' close=')'>#{s}</foreach></script>")
    List<Execution> selectByStatusIgnoreTenant(Collection<String> statuses);
}
