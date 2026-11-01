package com.swa.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.swa.backend.entity.LlmCallLog;
import org.apache.ibatis.annotations.Mapper;

/**
 * LlmCallLog Mapper，继承 MyBatis-Plus BaseMapper。
 */
@Mapper
public interface LlmCallLogMapper  extends BaseMapper<LlmCallLog> {
}
