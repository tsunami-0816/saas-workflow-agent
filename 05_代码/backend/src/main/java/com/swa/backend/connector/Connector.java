package com.swa.backend.connector;

import java.util.Map;

/**
 * 连接器 SPI（扩展锚点，BE-7.1）：新 SaaS 接入 = 新增实现类 + connector_credential 配置，不动引擎。
 */
public interface Connector {

    /**
     * 连接器类型标识，如 http / ocr-mock。
     */
    String type();

    /**
     * 执行连接器调用。
     *
     * @param config 节点配置（可含 credentialId 引用凭据）
     * @param input  节点输入
     * @return 输出
     */
    Map<String, Object> execute(Map<String, Object> config, Map<String, Object> input);
}
