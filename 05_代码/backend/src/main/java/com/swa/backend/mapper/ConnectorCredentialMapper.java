package com.swa.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.swa.backend.entity.ConnectorCredential;
import org.apache.ibatis.annotations.Mapper;

/**
 * ConnectorCredential Mapper，继承 MyBatis-Plus BaseMapper。
 */
@Mapper
public interface ConnectorCredentialMapper  extends BaseMapper<ConnectorCredential> {
}
