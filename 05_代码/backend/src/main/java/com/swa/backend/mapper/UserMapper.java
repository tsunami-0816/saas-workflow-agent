package com.swa.backend.mapper;

import cn.hutool.core.collection.CollUtil;
import com.baomidou.mybatisplus.annotation.InterceptorIgnore;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.swa.backend.entity.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * User Mapper，继承 MyBatis-Plus BaseMapper。
 */
@Mapper
public interface UserMapper extends BaseMapper<User> {

    /**
     * 登录专用：按用户名查用户（跨租户，登录前尚无租户上下文）。
     * 第 6 步冒烟修复：@InterceptorIgnore 标在 default 方法上不生效（真正执行的 MS 是 selectList，
     * 租户拦截器以 tenantId=0 过滤导致登录恒 401），改为标在真实执行的 @Select 方法上。
     * SQL 用标准语法（禁 LIMIT 方言，取首个在 Java 侧做）；显式 deleted = 0 对齐逻辑删除。
     */
    @InterceptorIgnore(tenantLine = "true")
    @Select("SELECT id, tenant_id, username, password_hash, display_name, role, status, deleted, created_at, updated_at "
            + "FROM user WHERE username = #{username} AND deleted = 0")
    List<User> selectByUsernameAcrossTenants(String username);

    /**
     * @param username 用户名
     * @return 首个匹配用户（username 在租户内唯一；跨租户重名取首个，密码校验兜底）
     */
    default User selectByUsernameIgnoreTenant(String username) {
        List<User> list = selectByUsernameAcrossTenants(username);
        return CollUtil.isEmpty(list) ? null : list.get(0);
    }
}
