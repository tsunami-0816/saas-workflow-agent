package com.swa.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.swa.backend.entity.FlowTemplate;
import org.apache.ibatis.annotations.Mapper;

/**
 * FlowTemplate Mapper，继承 MyBatis-Plus BaseMapper。
 */
@Mapper
public interface FlowTemplateMapper  extends BaseMapper<FlowTemplate> {
}
