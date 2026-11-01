package com.swa.backend.connector;

import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 连接器注册表：按 type 索引所有 Connector 实现（Spring 自动收集）。
 */
@Component
public class ConnectorRegistry {

    private final Map<String, Connector> connectors = new HashMap<>();

    public ConnectorRegistry(List<Connector> connectorList) {
        for (Connector c : connectorList) {
            connectors.put(c.type(), c);
        }
    }

    /**
     * 按类型取连接器，未注册抛 50001。
     */
    public Connector get(String type) {
        Connector c = connectors.get(type);
        if (c == null) {
            throw new BizException(ErrorCode.CONNECTOR_NOT_FOUND, type);
        }
        return c;
    }
}
