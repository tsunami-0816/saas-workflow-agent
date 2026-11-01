package com.swa.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.swa.backend.entity.Workflow;
import org.apache.ibatis.annotations.Mapper;

/**
 * Workflow Mapper，继承 MyBatis-Plus BaseMapper。
 */
@Mapper
public interface WorkflowMapper  extends BaseMapper<Workflow> {
}
