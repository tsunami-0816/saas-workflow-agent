package com.swa.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.swa.backend.entity.NodeExecution;
import org.apache.ibatis.annotations.Mapper;

/**
 * NodeExecution Mapper，继承 MyBatis-Plus BaseMapper。
 */
@Mapper
public interface NodeExecutionMapper  extends BaseMapper<NodeExecution> {
}
