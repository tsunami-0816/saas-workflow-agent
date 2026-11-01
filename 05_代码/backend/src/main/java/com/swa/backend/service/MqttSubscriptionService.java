package com.swa.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.dto.MqttSubscriptionRequest;
import com.swa.backend.entity.MqttSubscription;
import com.swa.backend.mapper.MqttSubscriptionMapper;
import com.swa.backend.mapper.WorkflowVersionMapper;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;

/**
 * MQTT 订阅管理（BE-7.4）：topic → workflow_version 绑定，uk(tenant_id,topic)。
 */
@Service
public class MqttSubscriptionService {

    private final MqttSubscriptionMapper subscriptionMapper;
    private final WorkflowVersionMapper versionMapper;

    public MqttSubscriptionService(MqttSubscriptionMapper subscriptionMapper,
                                   WorkflowVersionMapper versionMapper) {
        this.subscriptionMapper = subscriptionMapper;
        this.versionMapper = versionMapper;
    }

    public Page<MqttSubscription> page(int pageNo, int pageSize) {
        return subscriptionMapper.selectPage(new Page<>(pageNo, pageSize),
                new QueryWrapper<MqttSubscription>().orderByDesc("id"));
    }

    public MqttSubscription get(Long id) {
        MqttSubscription subscription = subscriptionMapper.selectById(id);
        if (subscription == null) {
            throw new BizException(ErrorCode.MQTT_SUBSCRIPTION_NOT_FOUND);
        }
        return subscription;
    }

    /**
     * 创建订阅：校验绑定版本存在；uk(tenant_id,topic) 冲突报 10000。
     */
    public MqttSubscription create(MqttSubscriptionRequest request) {
        checkVersion(request.workflowVersionId());
        MqttSubscription subscription = new MqttSubscription();
        subscription.setTopic(request.topic());
        subscription.setWorkflowVersionId(request.workflowVersionId());
        subscription.setStatus(request.status() == null ? "active" : request.status());
        try {
            subscriptionMapper.insert(subscription);
        } catch (DuplicateKeyException e) {
            throw new BizException(ErrorCode.PARAM_ERROR, "topic 已存在: " + request.topic());
        }
        return subscription;
    }

    public MqttSubscription update(Long id, MqttSubscriptionRequest request) {
        MqttSubscription subscription = get(id);
        checkVersion(request.workflowVersionId());
        subscription.setTopic(request.topic());
        subscription.setWorkflowVersionId(request.workflowVersionId());
        if (request.status() != null) {
            subscription.setStatus(request.status());
        }
        try {
            subscriptionMapper.updateById(subscription);
        } catch (DuplicateKeyException e) {
            throw new BizException(ErrorCode.PARAM_ERROR, "topic 已存在: " + request.topic());
        }
        return subscription;
    }

    public void delete(Long id) {
        get(id);
        subscriptionMapper.deleteById(id);
    }

    private void checkVersion(Long versionId) {
        if (versionMapper.selectById(versionId) == null) {
            throw new BizException(ErrorCode.VERSION_NOT_FOUND);
        }
    }
}
