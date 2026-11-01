package com.swa.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.swa.backend.entity.Tenant;
import org.apache.ibatis.annotations.Mapper;

/**
 * Tenant Mapper，继承 MyBatis-Plus BaseMapper。
 */
@Mapper
public interface TenantMapper  extends BaseMapper<Tenant> {
}
