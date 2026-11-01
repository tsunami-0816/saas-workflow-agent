package com.swa.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.swa.backend.entity.AuditLog;
import org.apache.ibatis.annotations.Mapper;

/**
 * AuditLog Mapper，继承 MyBatis-Plus BaseMapper。
 */
@Mapper
public interface AuditLogMapper  extends BaseMapper<AuditLog> {
}
