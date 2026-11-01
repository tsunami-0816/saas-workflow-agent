-- =============================================================
-- saas-workflow-agent 数据库初始化脚本（MySQL 8.x，utf8mb4）
-- 覆盖 12 张表 + 种子数据；可重复执行（先 DROP 再 CREATE）。
-- 字段命名与 com.swa.backend.entity 一一对应（下划线风格）。
-- =============================================================

CREATE DATABASE IF NOT EXISTS swa DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE swa;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS tenant;
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS tenant_quota;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS workflow;
DROP TABLE IF EXISTS workflow_version;
DROP TABLE IF EXISTS execution;
DROP TABLE IF EXISTS node_execution;
DROP TABLE IF EXISTS llm_call_log;
DROP TABLE IF EXISTS connector_credential;
DROP TABLE IF EXISTS mqtt_subscription;
DROP TABLE IF EXISTS flow_template;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. 租户表（系统表，不参与租户拦截）
CREATE TABLE tenant (
    id          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id   BIGINT       NOT NULL COMMENT '租户ID（=id，统一拦截口径）',
    name        VARCHAR(128) NOT NULL COMMENT '租户名',
    status      VARCHAR(16)  NOT NULL DEFAULT 'active' COMMENT 'active/disabled',
    deleted     TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_tenant_name (name)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT ='租户表';

-- 2. 用户表
CREATE TABLE user (
    id            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id     BIGINT       NOT NULL COMMENT '租户ID',
    username      VARCHAR(64)  NOT NULL COMMENT '登录名',
    password_hash VARCHAR(128) NOT NULL COMMENT 'BCrypt 哈希',
    display_name  VARCHAR(128) DEFAULT NULL COMMENT '显示名',
    role          VARCHAR(16)  NOT NULL COMMENT 'admin/dev/viewer',
    status        VARCHAR(16)  NOT NULL DEFAULT 'active' COMMENT 'active/disabled',
    deleted       TINYINT      NOT NULL DEFAULT 0,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_tenant_username (tenant_id, username)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT ='用户表';

-- 3. 租户额度表
CREATE TABLE tenant_quota (
    id          BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id   BIGINT NOT NULL COMMENT '租户ID',
    token_total BIGINT NOT NULL DEFAULT 0 COMMENT '总额度（token）',
    token_used  BIGINT NOT NULL DEFAULT 0 COMMENT '已用额度（token）',
    deleted     TINYINT NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_quota_tenant (tenant_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT ='租户额度表';

-- 4. 审计日志表
CREATE TABLE audit_log (
    id         BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id  BIGINT       NOT NULL COMMENT '租户ID',
    user_id    BIGINT       DEFAULT NULL COMMENT '操作人',
    action     VARCHAR(64)  NOT NULL COMMENT '动作，如 workflow.create',
    target     VARCHAR(256) DEFAULT NULL COMMENT '操作对象',
    detail     LONGTEXT     DEFAULT NULL COMMENT '明细（JSON 文本）',
    ip         VARCHAR(64)  DEFAULT NULL COMMENT '来源 IP',
    deleted    TINYINT      NOT NULL DEFAULT 0,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_audit_tenant_created (tenant_id, created_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT ='审计日志表';

-- 5. 流程表
CREATE TABLE workflow (
    id          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id   BIGINT       NOT NULL COMMENT '租户ID',
    name        VARCHAR(128) NOT NULL COMMENT '流程名',
    description VARCHAR(512) DEFAULT NULL COMMENT '描述',
    deleted     TINYINT      NOT NULL DEFAULT 0,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_workflow_tenant (tenant_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT ='流程表';

-- 6. 流程版本表
CREATE TABLE workflow_version (
    id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id   BIGINT      NOT NULL COMMENT '租户ID',
    workflow_id BIGINT      NOT NULL COMMENT '流程ID',
    version_no  INT         NOT NULL COMMENT '版本号（租户内递增）',
    dsl_json    LONGTEXT    NOT NULL COMMENT '画布 DSL JSON',
    status      VARCHAR(16) NOT NULL DEFAULT 'draft' COMMENT 'draft/published/disabled',
    deleted     TINYINT     NOT NULL DEFAULT 0,
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_version_workflow_no (workflow_id, version_no),
    KEY idx_version_tenant (tenant_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT ='流程版本表';

-- 7. 执行实例表
CREATE TABLE execution (
    id              BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id       BIGINT      NOT NULL COMMENT '租户ID',
    version_id      BIGINT      NOT NULL COMMENT '流程版本ID',
    user_id         BIGINT      DEFAULT NULL COMMENT '触发人（mqtt 触发为空）',
    status          VARCHAR(16) NOT NULL COMMENT 'RUNNING/SUCCESS/FAILED/WAITING',
    trigger_type    VARCHAR(16) NOT NULL DEFAULT 'manual' COMMENT 'manual/mqtt/replay',
    trigger_payload LONGTEXT    DEFAULT NULL COMMENT '触发输入（JSON 文本）',
    fail_reason     VARCHAR(64) DEFAULT NULL COMMENT '收敛原因，如 node_failed/engine_restart',
    started_at      DATETIME    DEFAULT NULL,
    ended_at        DATETIME    DEFAULT NULL,
    deleted         TINYINT     NOT NULL DEFAULT 0,
    created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_execution_tenant_status (tenant_id, status),
    KEY idx_execution_version (version_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT ='执行实例表';

-- 8. 节点执行表
CREATE TABLE node_execution (
    id            BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id     BIGINT      NOT NULL COMMENT '租户ID',
    execution_id  BIGINT      NOT NULL COMMENT '执行实例ID',
    node_id       VARCHAR(64) NOT NULL COMMENT 'DSL 节点ID',
    node_type     VARCHAR(32) NOT NULL COMMENT '节点类型',
    status        VARCHAR(16) NOT NULL COMMENT 'PENDING/RUNNING/SUCCESS/FAILED/SKIPPED/WAITING',
    input_json    LONGTEXT    DEFAULT NULL COMMENT '节点输入（JSON）',
    output_json   LONGTEXT    DEFAULT NULL COMMENT '节点输出（JSON）',
    retry_log     LONGTEXT    DEFAULT NULL COMMENT '重试日志（JSON 数组）',
    error_message TEXT        DEFAULT NULL COMMENT '失败信息（截断 1000 字符）',
    started_at    DATETIME    DEFAULT NULL,
    ended_at      DATETIME    DEFAULT NULL,
    deleted       TINYINT     NOT NULL DEFAULT 0,
    created_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_node_execution (execution_id),
    KEY idx_node_tenant (tenant_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT ='节点执行表';

-- 9. LLM 调用台账表
CREATE TABLE llm_call_log (
    id                BIGINT         NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id         BIGINT         NOT NULL COMMENT '租户ID（内部调用缺省为 0 占位）',
    user_id           BIGINT         DEFAULT NULL COMMENT '发起人',
    provider          VARCHAR(32)    NOT NULL COMMENT 'deepseek/openai-mock/claude-mock',
    model             VARCHAR(64)    NOT NULL COMMENT '模型名',
    task_type         VARCHAR(32)    NOT NULL COMMENT 'nl2flow/agent_reasoning 等',
    prompt_tokens     INT            NOT NULL DEFAULT 0,
    completion_tokens INT            NOT NULL DEFAULT 0,
    cost              DECIMAL(12, 6) NOT NULL DEFAULT 0 COMMENT '成本（占位价）',
    latency_ms        BIGINT         DEFAULT NULL,
    deleted           TINYINT        NOT NULL DEFAULT 0,
    created_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_llm_log_tenant_created (tenant_id, created_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT ='LLM 调用台账表';

-- 10. 连接器凭据表（config_json 整体 AES/CBC 加密入库）
CREATE TABLE connector_credential (
    id             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id      BIGINT       NOT NULL COMMENT '租户ID',
    connector_type VARCHAR(32)  NOT NULL COMMENT '连接器类型，如 http',
    name           VARCHAR(128) NOT NULL COMMENT '凭据名',
    config_json    LONGTEXT     NOT NULL COMMENT '加密密文：base64(iv):base64(ct)',
    deleted        TINYINT      NOT NULL DEFAULT 0,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_credential_tenant (tenant_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT ='连接器凭据表';

-- 11. MQTT 订阅绑定表
CREATE TABLE mqtt_subscription (
    id                  BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id           BIGINT       NOT NULL COMMENT '租户ID',
    topic               VARCHAR(256) NOT NULL COMMENT 'MQTT topic（支持 +/# 通配）',
    workflow_version_id BIGINT       NOT NULL COMMENT '绑定的流程版本ID',
    status              VARCHAR(16)  NOT NULL DEFAULT 'active' COMMENT 'active/disabled',
    deleted             TINYINT      NOT NULL DEFAULT 0,
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_mqtt_tenant_topic (tenant_id, topic)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT ='MQTT 订阅绑定表';

-- 12. 流程模板表（Qdrant 模板检索 P2 延期，本期只留表结构）
CREATE TABLE flow_template (
    id          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id   BIGINT       NOT NULL COMMENT '租户ID',
    workflow_id BIGINT       DEFAULT NULL COMMENT '来源流程ID',
    summary     VARCHAR(512) DEFAULT NULL COMMENT '模板摘要',
    vector_id   VARCHAR(64)  DEFAULT NULL COMMENT 'Qdrant 向量ID',
    deleted     TINYINT      NOT NULL DEFAULT 0,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_template_tenant (tenant_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT ='流程模板表';

-- =============================================================
-- 种子数据
-- 初始密码统一为 Swa@123456（BCrypt 哈希，hutool BCrypt.hashpw 生成并已 checkpw 验证）；
-- 生产部署必须立即修改。
-- =============================================================

INSERT INTO tenant (id, tenant_id, name, status) VALUES
(1, 1, 'acme', 'active'),
(2, 2, 'globex', 'active');

INSERT INTO user (id, tenant_id, username, password_hash, display_name, role, status) VALUES
(1, 1, 'admin_acme', '$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK', 'ACME 管理员', 'admin', 'active'),
(2, 1, 'dev_acme', '$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK', 'ACME 开发', 'dev', 'active'),
(3, 1, 'viewer_acme', '$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK', 'ACME 只读', 'viewer', 'active'),
(4, 2, 'admin_globex', '$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK', 'GLOBEX 管理员', 'admin', 'active'),
(5, 2, 'dev_globex', '$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK', 'GLOBEX 开发', 'dev', 'active'),
(6, 2, 'viewer_globex', '$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK', 'GLOBEX 只读', 'viewer', 'active');

INSERT INTO tenant_quota (id, tenant_id, token_total, token_used) VALUES
(1, 1, 1000000, 0),
(2, 2, 1000000, 0);

-- 示例流程：MQTT 温度采集 → 高温判断 →（true）HTTP 告警 /（false）记录正常
INSERT INTO workflow (id, tenant_id, name, description) VALUES
(1, 1, '设备高温告警流程', 'MQTT 温度超阈值触发 HTTP 告警，否则标记正常（冒烟演示用）');

INSERT INTO workflow_version (id, tenant_id, workflow_id, version_no, dsl_json, status) VALUES
(1, 1, 1, 1, '{"nodes":[{"id":"t1","type":"mqtt-trigger","name":"温度采集","config":{}},{"id":"c1","type":"condition","name":"高温判断","config":{"expression":"t1.payload.temp > 80"}},{"id":"h1","type":"http","name":"告警通知","config":{"url":"http://127.0.0.1:8083/actuator/health","method":"GET","timeoutMs":10000}},{"id":"d1","type":"code","name":"正常记录","config":{"expression":"''normal: '' + t1.payload.temp"}}],"edges":[{"source":"t1","target":"c1"},{"source":"c1","target":"h1","branch":"true"},{"source":"c1","target":"d1","branch":"false"}]}', 'published');

INSERT INTO mqtt_subscription (id, tenant_id, topic, workflow_version_id, status) VALUES
(1, 1, 'factory/+/temperature', 1, 'active');

-- 凭据示例：config_json 为占位符，真实密文请通过 POST /api/v1/credentials 创建（服务端自动 AES 加密）
INSERT INTO connector_credential (id, tenant_id, connector_type, name, config_json) VALUES
(1, 1, 'http', '示例告警服务凭据（占位）', 'PLACEHOLDER_ENCRYPTED__USE_API_TO_CREATE');
