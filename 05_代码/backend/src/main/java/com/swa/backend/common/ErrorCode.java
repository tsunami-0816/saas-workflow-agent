package com.swa.backend.common;

/**
 * 错误码分段（任务文档 §6.1）：
 * 1xxxx 通用/权限；2xxxx 流程定义；3xxxx 执行；4xxxx 模型路由；5xxxx 连接器；6xxxx Agent。
 */
public enum ErrorCode {

    // 1xxxx 通用/权限
    PARAM_ERROR(10000, "参数错误"),
    UNAUTHORIZED(10401, "未登录或凭证已失效"),
    FORBIDDEN(10403, "越权访问：角色无权执行该操作"),
    NOT_FOUND(10004, "资源不存在"),
    INTERNAL_ERROR(10500, "服务器内部错误"),

    // 2xxxx 流程定义
    WORKFLOW_NOT_FOUND(20001, "流程不存在"),
    DSL_CYCLE(20002, "DSL 校验失败：存在环形依赖"),
    DSL_UNKNOWN_NODE_TYPE(20003, "DSL 校验失败：未知节点类型"),
    DSL_DEGREE_INVALID(20004, "DSL 校验失败：节点入度/出度不合法"),
    DSL_DANGLING_EDGE(20005, "DSL 校验失败：连线指向不存在的节点"),
    DSL_INVALID(20006, "DSL 校验失败"),
    VERSION_NOT_FOUND(20007, "流程版本不存在"),
    VERSION_DISABLED(20008, "流程版本已禁用，不可执行"),
    VERSION_NOT_PUBLISHED(20009, "仅 published 状态版本可执行"),
    VERSION_STATUS_ILLEGAL(20010, "版本状态流转非法"),

    // 3xxxx 执行
    EXECUTION_NOT_FOUND(30001, "执行实例不存在"),
    EXECUTION_CREATE_FAILED(30002, "执行创建失败"),
    NODE_EXECUTION_FAILED(30003, "节点执行失败"),

    // 4xxxx 模型路由
    LLM_CALL_FAILED(40001, "LLM 调用失败"),
    LLM_UNKNOWN_TASK_TYPE(40002, "未知 taskType 或未配置路由"),
    QUOTA_EXCEEDED(40429, "租户额度超限"),
    NL_GENERATE_FAILED(40003, "NL 生成流程失败"),

    // 5xxxx 连接器
    CONNECTOR_NOT_FOUND(50001, "连接器不存在"),
    CREDENTIAL_NOT_FOUND(50002, "连接器凭据不存在"),
    MQTT_SUBSCRIPTION_NOT_FOUND(50003, "MQTT 订阅不存在"),
    HTTP_NODE_FAILED(50004, "HTTP 节点调用失败"),

    // 6xxxx Agent
    AGENT_CALL_FAILED(60001, "Agent 调用失败或超时");

    private final int code;
    private final String message;

    ErrorCode(int code, String message) {
        this.code = code;
        this.message = message;
    }

    public int getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }
}
