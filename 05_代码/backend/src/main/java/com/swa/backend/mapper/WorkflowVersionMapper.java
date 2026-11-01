package com.swa.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.swa.backend.entity.WorkflowVersion;
import org.apache.ibatis.annotations.Mapper;

/**
 * WorkflowVersion Mapper，继承 MyBatis-Plus BaseMapper。
 */
@Mapper
public interface WorkflowVersionMapper  extends BaseMapper<WorkflowVersion> {
}
