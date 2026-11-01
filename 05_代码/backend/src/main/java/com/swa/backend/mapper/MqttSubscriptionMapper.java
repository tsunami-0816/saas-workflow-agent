package com.swa.backend.mapper;

import com.baomidou.mybatisplus.annotation.InterceptorIgnore;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.swa.backend.entity.MqttSubscription;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MqttSubscription Mapper，继承 MyBatis-Plus BaseMapper。
 */
@Mapper
public interface MqttSubscriptionMapper  extends BaseMapper<MqttSubscription> {

    /**
     * 跨租户查询全部 active 订阅：MQTT 客户端启动/重订阅时加载（消息反查需匹配所有租户）。
     * 注意：@InterceptorIgnore 必须标注在真实执行的 SQL 方法上（default 方法桥接不生效）。
     */
    @InterceptorIgnore(tenantLine = "true")
    @Select("SELECT id, tenant_id, topic, workflow_version_id, status, deleted, created_at, updated_at "
            + "FROM mqtt_subscription WHERE status = 'active' AND deleted = 0")
    List<MqttSubscription> selectActiveIgnoreTenant();
}
