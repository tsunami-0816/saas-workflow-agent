package com.swa.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.swa.backend.entity.TenantQuota;
import org.apache.ibatis.annotations.Mapper;

/**
 * TenantQuota Mapper，继承 MyBatis-Plus BaseMapper。
 */
@Mapper
public interface TenantQuotaMapper  extends BaseMapper<TenantQuota> {
}
