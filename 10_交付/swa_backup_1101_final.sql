-- MySQL dump 10.13  Distrib 8.4.13, for Linux (x86_64)
--
-- Host: localhost    Database: swa
-- ------------------------------------------------------
-- Server version	8.4.13

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `audit_log`
--

DROP TABLE IF EXISTS `audit_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_log` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tenant_id` bigint NOT NULL COMMENT '租户ID',
  `user_id` bigint DEFAULT NULL COMMENT '操作人',
  `action` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '动作，如 workflow.create',
  `target` varchar(256) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '操作对象',
  `detail` longtext COLLATE utf8mb4_unicode_ci COMMENT '明细（JSON 文本）',
  `ip` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '来源 IP',
  `deleted` tinyint NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_audit_tenant_created` (`tenant_id`,`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_log`
--

LOCK TABLES `audit_log` WRITE;
/*!40000 ALTER TABLE `audit_log` DISABLE KEYS */;
INSERT INTO `audit_log` VALUES (1,1,1,'workflow.create','WorkflowController.create(..)','WorkflowCreateRequest[name=验收走查-全节点-db1e1a, description=覆盖 6 类节点/双分支/延时/Agent];','0:0:0:0:0:0:0:1',0,'2026-11-01 09:48:57','2026-11-01 09:48:57'),(2,1,1,'workflow.version.save','WorkflowController.saveVersion(..)','2;VersionSaveRequest[dslJson={\"nodes\": [{\"id\": \"t1\", \"type\": \"mqtt-trigger\", \"name\": \"温度采集\", \"config\": {}}, {\"id\": \"c1\", \"type\": \"condition\", \"name\": \"高温判断\", \"config\": {\"expression\": \"t1.payload.temp > ;','0:0:0:0:0:0:0:1',0,'2026-11-01 09:48:59','2026-11-01 09:48:59'),(3,1,1,'workflow.version.publish','WorkflowController.publish(..)','2;','0:0:0:0:0:0:0:1',0,'2026-11-01 09:49:00','2026-11-01 09:49:00'),(4,1,1,'execution.create','ExecutionController.create(..)','ExecutionCreateRequest[versionId=2, clientReqId=3ccbb7922529443c, triggerPayload={\"temp\": 95}];','0:0:0:0:0:0:0:1',0,'2026-11-01 09:49:00','2026-11-01 09:49:00'),(5,1,1,'execution.create','ExecutionController.create(..)','ExecutionCreateRequest[versionId=2, clientReqId=3ccbb7922529443c, triggerPayload={\"temp\": 95}];','0:0:0:0:0:0:0:1',0,'2026-11-01 09:49:01','2026-11-01 09:49:01'),(6,1,1,'execution.create','ExecutionController.create(..)','ExecutionCreateRequest[versionId=2, clientReqId=38a4494578894a0e, triggerPayload={\"temp\": 95}];','0:0:0:0:0:0:0:1',0,'2026-11-01 09:49:24','2026-11-01 09:49:24'),(7,1,1,'execution.create','ExecutionController.create(..)','ExecutionCreateRequest[versionId=2, clientReqId=be6388533da14767, triggerPayload={\"temp\": 25}];','0:0:0:0:0:0:0:1',0,'2026-11-01 09:50:01','2026-11-01 09:50:01'),(8,1,1,'execution.replay','ExecutionController.replay(..)','1;','0:0:0:0:0:0:0:1',0,'2026-11-01 09:50:03','2026-11-01 09:50:03'),(9,1,1,'workflow.nl-draft','WorkflowController.nlDraft(..)','NlDraftRequest[text=当设备温度超过 80 度时发 HTTP 告警，否则记录到日志, workflowName=NL验收-温度告警];','0:0:0:0:0:0:0:1',0,'2026-11-01 09:50:09','2026-11-01 09:50:09'),(10,1,1,'workflow.delete','WorkflowController.delete(..)','2;','0:0:0:0:0:0:0:1',0,'2026-11-01 09:50:21','2026-11-01 09:50:21');
/*!40000 ALTER TABLE `audit_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `connector_credential`
--

DROP TABLE IF EXISTS `connector_credential`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `connector_credential` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tenant_id` bigint NOT NULL COMMENT '租户ID',
  `connector_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '连接器类型，如 http',
  `name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '凭据名',
  `config_json` longtext COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '加密密文：base64(iv):base64(ct)',
  `deleted` tinyint NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_credential_tenant` (`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='连接器凭据表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `connector_credential`
--

LOCK TABLES `connector_credential` WRITE;
/*!40000 ALTER TABLE `connector_credential` DISABLE KEYS */;
INSERT INTO `connector_credential` VALUES (1,1,'http','示例告警服务凭据（占位）','PLACEHOLDER_ENCRYPTED__USE_API_TO_CREATE',0,'2026-11-01 05:58:29','2026-11-01 05:58:29');
/*!40000 ALTER TABLE `connector_credential` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `execution`
--

DROP TABLE IF EXISTS `execution`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `execution` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tenant_id` bigint NOT NULL COMMENT '租户ID',
  `version_id` bigint NOT NULL COMMENT '流程版本ID',
  `user_id` bigint DEFAULT NULL COMMENT '触发人（mqtt 触发为空）',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'RUNNING/SUCCESS/FAILED/WAITING',
  `trigger_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'manual' COMMENT 'manual/mqtt/replay',
  `trigger_payload` longtext COLLATE utf8mb4_unicode_ci COMMENT '触发输入（JSON 文本）',
  `fail_reason` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '收敛原因，如 node_failed/engine_restart',
  `started_at` datetime DEFAULT NULL,
  `ended_at` datetime DEFAULT NULL,
  `deleted` tinyint NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_execution_tenant_status` (`tenant_id`,`status`),
  KEY `idx_execution_version` (`version_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='执行实例表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `execution`
--

LOCK TABLES `execution` WRITE;
/*!40000 ALTER TABLE `execution` DISABLE KEYS */;
INSERT INTO `execution` VALUES (1,1,2,1,'SUCCESS','manual','{\"temp\": 95}',NULL,'2026-11-01 17:49:01','2026-11-01 17:49:19',0,'2026-11-01 09:49:00','2026-11-01 09:49:00'),(2,1,2,1,'SUCCESS','manual','{\"temp\": 95}',NULL,'2026-11-01 17:49:24','2026-11-01 17:49:58',0,'2026-11-01 09:49:23','2026-11-01 09:49:23'),(3,1,2,1,'SUCCESS','manual','{\"temp\": 25}',NULL,'2026-11-01 17:50:02','2026-11-01 17:50:02',0,'2026-11-01 09:50:01','2026-11-01 09:50:01'),(4,1,2,1,'SUCCESS','replay','{\"temp\": 95}',NULL,'2026-11-01 17:50:03','2026-11-01 17:50:27',0,'2026-11-01 09:50:03','2026-11-01 09:50:03'),(5,1,1,NULL,'SUCCESS','mqtt','{\"temp\": 95}',NULL,'2026-11-01 17:50:14','2026-11-01 17:50:15',0,'2026-11-01 09:50:14','2026-11-01 09:50:14');
/*!40000 ALTER TABLE `execution` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `flow_template`
--

DROP TABLE IF EXISTS `flow_template`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flow_template` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tenant_id` bigint NOT NULL COMMENT '租户ID',
  `workflow_id` bigint DEFAULT NULL COMMENT '来源流程ID',
  `summary` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '模板摘要',
  `vector_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Qdrant 向量ID',
  `deleted` tinyint NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_template_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='流程模板表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `flow_template`
--

LOCK TABLES `flow_template` WRITE;
/*!40000 ALTER TABLE `flow_template` DISABLE KEYS */;
/*!40000 ALTER TABLE `flow_template` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `llm_call_log`
--

DROP TABLE IF EXISTS `llm_call_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `llm_call_log` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tenant_id` bigint NOT NULL COMMENT '租户ID（内部调用缺省为 0 占位）',
  `user_id` bigint DEFAULT NULL COMMENT '发起人',
  `provider` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'deepseek/openai-mock/claude-mock',
  `model` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '模型名',
  `task_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'nl2flow/agent_reasoning 等',
  `prompt_tokens` int NOT NULL DEFAULT '0',
  `completion_tokens` int NOT NULL DEFAULT '0',
  `cost` decimal(12,6) NOT NULL DEFAULT '0.000000' COMMENT '成本（占位价）',
  `latency_ms` bigint DEFAULT NULL,
  `deleted` tinyint NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_llm_log_tenant_created` (`tenant_id`,`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='LLM 调用台账表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `llm_call_log`
--

LOCK TABLES `llm_call_log` WRITE;
/*!40000 ALTER TABLE `llm_call_log` DISABLE KEYS */;
INSERT INTO `llm_call_log` VALUES (1,1,NULL,'dashscope','qwen-plus','agent_reasoning',224,498,0.002888,11477,0,'2026-11-01 09:49:17','2026-11-01 09:49:17'),(2,1,NULL,'dashscope','qwen-plus','agent_reasoning',715,13,0.002912,772,0,'2026-11-01 09:49:18','2026-11-01 09:49:18'),(3,1,NULL,'dashscope','qwen-plus','agent_reasoning',669,13,0.002728,611,0,'2026-11-01 09:49:19','2026-11-01 09:49:19'),(4,1,NULL,'dashscope','qwen-plus','agent_reasoning',224,389,0.002452,8927,0,'2026-11-01 09:49:38','2026-11-01 09:49:38'),(5,1,NULL,'dashscope','qwen-plus','agent_reasoning',607,418,0.004100,9503,0,'2026-11-01 09:49:47','2026-11-01 09:49:47'),(6,1,NULL,'dashscope','qwen-plus','agent_reasoning',966,453,0.005676,10247,0,'2026-11-01 09:49:57','2026-11-01 09:49:57'),(7,1,1,'dashscope','qwen-plus','nl2flow',566,171,0.002948,4176,0,'2026-11-01 09:50:09','2026-11-01 09:50:09'),(8,1,NULL,'dashscope','qwen-plus','agent_reasoning',224,405,0.002516,9268,0,'2026-11-01 09:50:17','2026-11-01 09:50:17'),(9,1,NULL,'dashscope','qwen-plus','agent_reasoning',622,361,0.003932,8252,0,'2026-11-01 09:50:26','2026-11-01 09:50:26'),(10,1,NULL,'dashscope','qwen-plus','agent_reasoning',925,11,0.003744,622,0,'2026-11-01 09:50:26','2026-11-01 09:50:26');
/*!40000 ALTER TABLE `llm_call_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `mqtt_subscription`
--

DROP TABLE IF EXISTS `mqtt_subscription`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mqtt_subscription` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tenant_id` bigint NOT NULL COMMENT '租户ID',
  `topic` varchar(256) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'MQTT topic（支持 +/# 通配）',
  `workflow_version_id` bigint NOT NULL COMMENT '绑定的流程版本ID',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT 'active/disabled',
  `deleted` tinyint NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_mqtt_tenant_topic` (`tenant_id`,`topic`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MQTT 订阅绑定表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `mqtt_subscription`
--

LOCK TABLES `mqtt_subscription` WRITE;
/*!40000 ALTER TABLE `mqtt_subscription` DISABLE KEYS */;
INSERT INTO `mqtt_subscription` VALUES (1,1,'factory/+/temperature',1,'active',0,'2026-11-01 05:58:29','2026-11-01 05:58:29');
/*!40000 ALTER TABLE `mqtt_subscription` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `node_execution`
--

DROP TABLE IF EXISTS `node_execution`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `node_execution` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tenant_id` bigint NOT NULL COMMENT '租户ID',
  `execution_id` bigint NOT NULL COMMENT '执行实例ID',
  `node_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'DSL 节点ID',
  `node_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '节点类型',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'PENDING/RUNNING/SUCCESS/FAILED/SKIPPED/WAITING',
  `input_json` longtext COLLATE utf8mb4_unicode_ci COMMENT '节点输入（JSON）',
  `output_json` longtext COLLATE utf8mb4_unicode_ci COMMENT '节点输出（JSON）',
  `retry_log` longtext COLLATE utf8mb4_unicode_ci COMMENT '重试日志（JSON 数组）',
  `error_message` text COLLATE utf8mb4_unicode_ci COMMENT '失败信息（截断 1000 字符）',
  `started_at` datetime DEFAULT NULL,
  `ended_at` datetime DEFAULT NULL,
  `deleted` tinyint NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_node_execution` (`execution_id`),
  KEY `idx_node_tenant` (`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='节点执行表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `node_execution`
--

LOCK TABLES `node_execution` WRITE;
/*!40000 ALTER TABLE `node_execution` DISABLE KEYS */;
INSERT INTO `node_execution` VALUES (1,1,1,'t1','mqtt-trigger','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95}}','{\"payload\":{\"temp\":95}}','[]',NULL,'2026-11-01 17:49:01','2026-11-01 17:49:01',0,'2026-11-01 09:49:00','2026-11-01 09:49:00'),(2,1,1,'c1','condition','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"t1\":{\"payload\":{\"temp\":95}}}','{\"branch\":true}','[]',NULL,'2026-11-01 17:49:01','2026-11-01 17:49:01',0,'2026-11-01 09:49:00','2026-11-01 09:49:00'),(3,1,1,'h1','http','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"t1\":{\"payload\":{\"temp\":95}},\"c1\":{\"branch\":true}}','{\"body\":\"{\\\"status\\\":\\\"UP\\\"}\",\"latencyMs\":71,\"status\":200}','[]',NULL,'2026-11-01 17:49:01','2026-11-01 17:49:01',0,'2026-11-01 09:49:00','2026-11-01 09:49:00'),(4,1,1,'d1','code','SKIPPED',NULL,NULL,NULL,NULL,NULL,'2026-11-01 17:49:01',0,'2026-11-01 09:49:00','2026-11-01 09:49:00'),(5,1,1,'dly1','delay','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"h1\":{\"body\":\"{\\\"status\\\":\\\"UP\\\"}\",\"latencyMs\":71,\"status\":200},\"t1\":{\"payload\":{\"temp\":95}},\"c1\":{\"branch\":true}}','{\"resumed\":true}',NULL,NULL,'2026-11-01 17:49:01','2026-11-01 17:49:06',0,'2026-11-01 09:49:00','2026-11-01 09:49:00'),(6,1,1,'a1','agent','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"h1\":{\"body\":\"{\\\"status\\\":\\\"UP\\\"}\",\"latencyMs\":71,\"status\":200},\"t1\":{\"payload\":{\"temp\":95}},\"c1\":{\"branch\":true},\"dly1\":{\"resumed\":true}}','{\"output\":{\"plan\":\"1. **提取核心温度读数**  \\n   - 目标：从输入数据中准确定位并提取唯一有效的温度值（`temp` 字段）；  \\n   - 验收要点：确认所有嵌套结构（`_payload`、`payload`、`t1.payload`）中 `temp` 值均为 95，无冲突或歧义，最终采用该一致值作为判定依据。\\n\\n2. **确定告警阈值与判断逻辑**  \\n   - 目标：明确温度告警的业务阈值（如默认工业/设备场景常见高温阈值为 ≥90℃ 触发告警），并在无显式约束时采用合理默认；  \\n   - 验收要点：说明所采用阈值（如“90℃”）及其依据（如行业通用安全限值），并验证 95 > 90，满足告警触发条件。\\n\\n3. **生成中文总结句并嵌入告警判断**  \\n   - 目标：构造一句完整、无歧义的中文语句，包含温度读数和明确的告警结论（“需要告警”或“无需告警”）；  \\n   - 验收要点：句子结构为“本次温度读数为XX℃，[需要/无需]告警”，其中数值准确（95）、结论与步骤2逻辑严格一致（需告警）。\\n\\n4. **交叉验证数据一致性与异常信号**  \\n   - 目标：检查非温度字段（如 `h1.status=200`、`c1.branch=true`、`dly1.resumed=true`）是否暗示系统状态异常，可能影响温度可信度；  \\n   - 验收要点：确认所有辅助字段表征服务健康（HTTP 200、分支启用、延迟恢复），无矛盾证据否定温度读数有效性，支撑告警结论可靠。\\n\\n5. **输出最终总结句并标记可验证性**  \\n   - 目标：输出符合任务要求的单句结果，并确保该句可被独立复核（即仅依赖输入数据与公开阈值规则）；  \\n   - 验收要点：输出格式为纯中文句子，不含代码、注释或额外解释；内容可被第三方基于相同输入和阈值规则重复验证。\",\"result\":\"本次温度读数为95℃，需要告警。\",\"review\":\"本次温度读数为95℃，需要告警。\",\"final\":\"本次温度读数为95℃，需要告警。\"},\"reasoning\":[{\"step\":1,\"node\":\"planner\",\"thought\":\"先理解任务与约束，制定分步执行计划\",\"action\":\"Planner.run_role\",\"observation\":\"1. **提取核心温度读数**  \\n   - 目标：从输入数据中准确定位并提取唯一有效的温度值（`temp` 字段）；  \\n   - 验收要点：确认所有嵌套结构（`_payload`、`payload`、`t1.payload`）中 `temp` 值均为 95，无冲突或歧义，最终采用该一致值作为判定依据。\\n\\n2. **确定告警阈值与判断逻辑**  \\n   - 目标：明确温度告警的业务阈值（如默认工业/设备场景常见高温阈值为 ≥90℃ 触发告警），并在无显式约束时采用合理默认；  \\n   - 验收要点：说明所采用阈值（如“90℃”）及其依据（如行业通用安全限值），并验证 95 > 90，满足告警触发条件。\\n\\n3. **生成中文总结句并嵌入告警判断**  \\n   - 目标：构造一句完整、无歧义的中文语句，包含温度读数和明确的告警结论（“需要告警”或“无需告警”）；  \\n   - 验收要点：句子结构为“本次温度读数为XX℃，[需要/无需]告警”，其中数值准确（95）、结论与步骤2逻辑严格一致（需告警）。\\n\\n4. **交叉验证数据一致性与异常信号**  \\n   - 目标：检查非温度字段（如 `h1.status=200`、`c1.branch=true`、`dly1.resumed=true`）是否暗示系统状态异常，可能影响温度可信度；  \\n   - 验收要点：确认所有辅助字段表征服务健康（HTTP 200、分支启用、延迟恢复），无矛盾证据否定温度读数有效性，支撑告警结论可靠。\\n\\n5. **输出最终总结句并标记可验证性**  \\n   - 目标：输出符合任务要求的单句结果，并确保该句可被独立复核（即仅依赖输入数据与公开阈值规则）；  \\n   - 验收要点：输出格式为纯中文句子，不含代码、注释或额外解释；内容可被第三方基于相同输入和阈值规则重复验证。\"},{\"step\":2,\"node\":\"executor\",\"thought\":\"按计划逐步执行，产出结果草稿\",\"action\":\"Executor.run_role\",\"observation\":\"本次温度读数为95℃，需要告警。\"},{\"step\":3,\"node\":\"reviewer\",\"thought\":\"审核结果正确性/完整性/约束符合度，输出最终交付\",\"action\":\"Reviewer.run_role\",\"observation\":\"本次温度读数为95℃，需要告警。\"}],\"durationMs\":13062}','[]',NULL,'2026-11-01 17:49:06','2026-11-01 17:49:19',0,'2026-11-01 09:49:00','2026-11-01 09:49:00'),(7,1,2,'t1','mqtt-trigger','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95}}','{\"payload\":{\"temp\":95}}','[]',NULL,'2026-11-01 17:49:24','2026-11-01 17:49:24',0,'2026-11-01 09:49:23','2026-11-01 09:49:23'),(8,1,2,'c1','condition','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"t1\":{\"payload\":{\"temp\":95}}}','{\"branch\":true}','[]',NULL,'2026-11-01 17:49:24','2026-11-01 17:49:24',0,'2026-11-01 09:49:23','2026-11-01 09:49:23'),(9,1,2,'h1','http','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"t1\":{\"payload\":{\"temp\":95}},\"c1\":{\"branch\":true}}','{\"body\":\"{\\\"status\\\":\\\"UP\\\"}\",\"latencyMs\":25,\"status\":200}','[]',NULL,'2026-11-01 17:49:24','2026-11-01 17:49:24',0,'2026-11-01 09:49:23','2026-11-01 09:49:23'),(10,1,2,'d1','code','SKIPPED',NULL,NULL,NULL,NULL,NULL,'2026-11-01 17:49:24',0,'2026-11-01 09:49:23','2026-11-01 09:49:23'),(11,1,2,'dly1','delay','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"h1\":{\"body\":\"{\\\"status\\\":\\\"UP\\\"}\",\"latencyMs\":25,\"status\":200},\"t1\":{\"payload\":{\"temp\":95}},\"c1\":{\"branch\":true}}','{\"resumed\":true}',NULL,NULL,'2026-11-01 17:49:24','2026-11-01 17:49:29',0,'2026-11-01 09:49:24','2026-11-01 09:49:24'),(12,1,2,'a1','agent','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"h1\":{\"body\":\"{\\\"status\\\":\\\"UP\\\"}\",\"latencyMs\":25,\"status\":200},\"t1\":{\"payload\":{\"temp\":95}},\"c1\":{\"branch\":true},\"dly1\":{\"resumed\":true}}','{\"output\":{\"plan\":\"1. **提取核心温度读数**  \\n　　目标：从输入数据中准确定位并提取唯一有效的温度值（单位：℃）；  \\n　　验收要点：确认 `temp = 95` 来自至少一个权威字段（如 `payload.temp` 或 `_payload.temp`），排除冗余或嵌套干扰（如 `h1.body` 为 JSON 字符串，非数值源）。\\n\\n2. **确定告警阈值基准**  \\n　　目标：明确判断“是否需要告警”的客观标准；  \\n　　验收要点：因任务未提供阈值约束，需显式声明默认工业/通用安全阈值（如：≥85℃ 触发高温告警），并记录该假设为关键前提。\\n\\n3. **执行温度比对与告警判定**  \\n　　目标：将提取的温度值（95℃）与上步确定的阈值比较，输出布尔判定结果；  \\n　　验收要点：95 ≥ 85 → 判定为“需要告警”，结论必须逻辑可追溯，不可模糊表述（如“偏高”“异常”）。\\n\\n4. **生成符合要求的中文单句总结**  \\n　　目标：整合温度读数与告警判定，输出严格满足“一句话”格式的自然语言结论；  \\n　　验收要点：句子结构为“本次温度读数为XX℃，[需要/不需要]告警”，无额外解释、标点错误或信息冗余。\\n\\n5. **验证输出合规性**  \\n　　目标：确保最终句子完全基于步骤1–4推导，且不引入外部知识或未声明假设；  \\n　　验收要点：句子可被独立复现（给定相同输入和步骤2的阈值假设，必得相同输出）。\",\"result\":\"1. **提取核心温度读数**  \\n　　从输入数据中，`_payload.temp = 95`、`payload.temp = 95`、`t1.payload.temp = 95` 均一致指向有效数值；其中 `_payload.temp` 和 `payload.temp` 为顶层直接可解析的权威字段，满足“至少一个权威字段”要求；排除 `h1.body`（为 JSON 字符串，非数值源）等干扰项。确认唯一有效温度值：**temp = 95℃**。\\n\\n2. **确定告警阈值基准**  \\n　　任务未提供具体阈值，依据工业通用安全规范（如IEC 60721-3-3、GB/T 17626.2 中对电子设备运行温度的典型限值），设定默认高温告警阈值为 **≥85℃**；此为显式声明的关键前提，用于后续判定。\\n\\n3. **执行温度比对与告警判定**  \\n　　95℃ ≥ 85℃ → 满足告警触发条件 → 判定结果为：**需要告警**；逻辑链清晰、可追溯，无模糊表述。\\n\\n4. **生成符合要求的中文单句总结**  \\n　　按结构“本次温度读数为XX℃，[需要/不需要]告警”，代入数值与判定：**本次温度读数为95℃，需要告警**。\\n\\n5. **验证输出合规性**  \\n　　句子完全基于步骤1提取值（95）、步骤2设定阈值（85）、步骤3比较结果（95≥85→需要）、步骤4格式约束生成；无额外解释、无标点错误、无信息冗余；给定相同输入和相同阈值假设，复现结果唯一且确定。\\n\\n**最终输出：**  \\n本次温度读数为95℃，需要告警。\",\"review\":\"审核发现以下问题：\\n\\n1. **阈值基准声明不满足约束合规性**：任务明确约束为 `{}`（空对象），即**禁止引入任何未提供的外部规范或标准**。步骤2中援引“IEC 60721-3-3、GB/T 17626.2”及“工业通用安全规范”属于未经允许的外部知识引入，违反“不引入外部知识或未声明假设”的验收要点（步骤5）与任务约束 `{}`。阈值设定必须严格基于任务上下文——而任务未提供阈值，故**不可自行设定85℃**；正确做法是：显式指出阈值缺失导致判定无法完成，并按最小可行原则采用任务隐含的逻辑闭环要求——即：若必须输出告警判定，则阈值必须可推导或必须声明为未定义。\\n\\n2. **执行结果草稿第4步生成的句子隐含错误前提**：在阈值未定义的前提下断言“需要告警”，构成逻辑谬误（无基准的比较无效）。该结论不可追溯，违反步骤3“逻辑可追溯”和步骤5“可被独立复现”的要求。\\n\\n3. **完整性缺失**：未响应约束 `{}` 的核心含义——空约束即**零假设、零扩展、零补充**。所有判断必须基于输入数据本身可直接导出的信息。温度值95℃存在，但“是否需要告警”是一个二元决策，其真值依赖阈值；阈值未提供 → 该命题为**真值未定（undetermined）**，而非默认触发。\\n\\n4. **修订原则**：  \\n　　- 保留准确提取的温度值（95℃）；  \\n　　- 显式声明阈值缺失，拒绝无效判定；  \\n　　- 仍满足“一句话”格式、中文、无冗余；  \\n　　- 结论须真实、可验证、不越界。\\n\\n**最终交付版本：**  \\n本次温度读数为95℃，因告警阈值未提供，无法判定是否需要告警。\",\"final\":\"审核发现以下问题：\\n\\n1. **阈值基准声明不满足约束合规性**：任务明确约束为 `{}`（空对象），即**禁止引入任何未提供的外部规范或标准**。步骤2中援引“IEC 60721-3-3、GB/T 17626.2”及“工业通用安全规范”属于未经允许的外部知识引入，违反“不引入外部知识或未声明假设”的验收要点（步骤5）与任务约束 `{}`。阈值设定必须严格基于任务上下文——而任务未提供阈值，故**不可自行设定85℃**；正确做法是：显式指出阈值缺失导致判定无法完成，并按最小可行原则采用任务隐含的逻辑闭环要求——即：若必须输出告警判定，则阈值必须可推导或必须声明为未定义。\\n\\n2. **执行结果草稿第4步生成的句子隐含错误前提**：在阈值未定义的前提下断言“需要告警”，构成逻辑谬误（无基准的比较无效）。该结论不可追溯，违反步骤3“逻辑可追溯”和步骤5“可被独立复现”的要求。\\n\\n3. **完整性缺失**：未响应约束 `{}` 的核心含义——空约束即**零假设、零扩展、零补充**。所有判断必须基于输入数据本身可直接导出的信息。温度值95℃存在，但“是否需要告警”是一个二元决策，其真值依赖阈值；阈值未提供 → 该命题为**真值未定（undetermined）**，而非默认触发。\\n\\n4. **修订原则**：  \\n　　- 保留准确提取的温度值（95℃）；  \\n　　- 显式声明阈值缺失，拒绝无效判定；  \\n　　- 仍满足“一句话”格式、中文、无冗余；  \\n　　- 结论须真实、可验证、不越界。\\n\\n**最终交付版本：**  \\n本次温度读数为95℃，因告警阈值未提供，无法判定是否需要告警。\"},\"reasoning\":[{\"step\":1,\"node\":\"planner\",\"thought\":\"先理解任务与约束，制定分步执行计划\",\"action\":\"Planner.run_role\",\"observation\":\"1. **提取核心温度读数**  \\n　　目标：从输入数据中准确定位并提取唯一有效的温度值（单位：℃）；  \\n　　验收要点：确认 `temp = 95` 来自至少一个权威字段（如 `payload.temp` 或 `_payload.temp`），排除冗余或嵌套干扰（如 `h1.body` 为 JSON 字符串，非数值源）。\\n\\n2. **确定告警阈值基准**  \\n　　目标：明确判断“是否需要告警”的客观标准；  \\n　　验收要点：因任务未提供阈值约束，需显式声明默认工业/通用安全阈值（如：≥85℃ 触发高温告警），并记录该假设为关键前提。\\n\\n3. **执行温度比对与告警判定**  \\n　　目标：将提取的温度值（95℃）与上步确定的阈值比较，输出布尔判定结果；  \\n　　验收要点：95 ≥ 85 → 判定为“需要告警”，结论必须逻辑可追溯，不可模糊表述（如“偏高”“异常”）。\\n\\n4. **生成符合要求的中文单句总结**  \\n　　目标：整合温度读数与告警判定，输出严格满足“一句话”格式的自然语言结论；  \\n　　验收要点：句子结构为“本次温度读数为XX℃，[需要/不需要]告警”，无额外解释、标点错误或信息冗余。\\n\\n5. **验证输出合规性**  \\n　　目标：确保最终句子完全基于步骤1–4推导，且不引入外部知识或未声明假设；  \\n　　验收要点：句子可被独立复现（给定相同输入和步骤2的阈值假设，必得相同输出）。\"},{\"step\":2,\"node\":\"executor\",\"thought\":\"按计划逐步执行，产出结果草稿\",\"action\":\"Executor.run_role\",\"observation\":\"1. **提取核心温度读数**  \\n　　从输入数据中，`_payload.temp = 95`、`payload.temp = 95`、`t1.payload.temp = 95` 均一致指向有效数值；其中 `_payload.temp` 和 `payload.temp` 为顶层直接可解析的权威字段，满足“至少一个权威字段”要求；排除 `h1.body`（为 JSON 字符串，非数值源）等干扰项。确认唯一有效温度值：**temp = 95℃**。\\n\\n2. **确定告警阈值基准**  \\n　　任务未提供具体阈值，依据工业通用安全规范（如IEC 60721-3-3、GB/T 17626.2 中对电子设备运行温度的典型限值），设定默认高温告警阈值为 **≥85℃**；此为显式声明的关键前提，用于后续判定。\\n\\n3. **执行温度比对与告警判定**  \\n　　95℃ ≥ 85℃ → 满足告警触发条件 → 判定结果为：**需要告警**；逻辑链清晰、可追溯，无模糊表述。\\n\\n4. **生成符合要求的中文单句总结**  \\n　　按结构“本次温度读数为XX℃，[需要/不需要]告警”，代入数值与判定：**本次温度读数为95℃，需要告警**。\\n\\n5. **验证输出合规性**  \\n　　句子完全基于步骤1提取值（95）、步骤2设定阈值（85）、步骤3比较结果（95≥85→需要）、步骤4格式约束生成；无额外解释、无标点错误、无信息冗余；给定相同输入和相同阈值假设，复现结果唯一且确定。\\n\\n**最终输出：**  \\n本次温度读数为95℃，需要告警。\"},{\"step\":3,\"node\":\"reviewer\",\"thought\":\"审核结果正确性/完整性/约束符合度，输出最终交付\",\"action\":\"Reviewer.run_role\",\"observation\":\"审核发现以下问题：\\n\\n1. **阈值基准声明不满足约束合规性**：任务明确约束为 `{}`（空对象），即**禁止引入任何未提供的外部规范或标准**。步骤2中援引“IEC 60721-3-3、GB/T 17626.2”及“工业通用安全规范”属于未经允许的外部知识引入，违反“不引入外部知识或未声明假设”的验收要点（步骤5）与任务约束 `{}`。阈值设定必须严格基于任务上下文——而任务未提供阈值，故**不可自行设定85℃**；正确做法是：显式指出阈值缺失导致判定无法完成，并按最小可行原则采用任务隐含的逻辑闭环要求——即：若必须输出告警判定，则阈值必须可推导或必须声明为未定义。\\n\\n2. **执行结果草稿第4步生成的句子隐含错误前提**：在阈值未定义的前提下断言“需要告警”，构成逻辑谬误（无基准的比较无效）。该结论不可追溯，违反步骤3“逻辑可追溯”和步骤5“可被独立复现”的要求。\\n\\n3. **完整性缺失**：未响应约束 `{}` 的核心含义——空约束即**零假设、零扩展、零补充**。所有判断必须基于输入数据本身可直接导出的信息。温度值95℃存在，但“是否需要告警”是一个二元决策，其真值依赖阈值；阈值未提供 → 该命题为**真值未定（undetermined）**，而非默认触发。\\n\\n4. **修订原则**：  \\n　　- 保留准确提取的温度值（95℃）；  \\n　　- 显式声明阈值缺失，拒绝无效判定；  \\n　　- 仍满足“一句话”格式、中文、无冗余；  \\n　　- 结论须真实、可验证、不越界。\\n\\n**最终交付版本：**  \\n本次温度读数为95℃，因告警阈值未提供，无法判定是否需要告警。\"}],\"durationMs\":28796}','[]',NULL,'2026-11-01 17:49:29','2026-11-01 17:49:58',0,'2026-11-01 09:49:24','2026-11-01 09:49:24'),(13,1,3,'t1','mqtt-trigger','SUCCESS','{\"_payload\":{\"temp\":25},\"payload\":{\"temp\":25}}','{\"payload\":{\"temp\":25}}','[]',NULL,'2026-11-01 17:50:02','2026-11-01 17:50:02',0,'2026-11-01 09:50:01','2026-11-01 09:50:01'),(14,1,3,'c1','condition','SUCCESS','{\"_payload\":{\"temp\":25},\"payload\":{\"temp\":25},\"t1\":{\"payload\":{\"temp\":25}}}','{\"branch\":false}','[]',NULL,'2026-11-01 17:50:02','2026-11-01 17:50:02',0,'2026-11-01 09:50:01','2026-11-01 09:50:01'),(15,1,3,'h1','http','SKIPPED',NULL,NULL,NULL,NULL,NULL,'2026-11-01 17:50:02',0,'2026-11-01 09:50:01','2026-11-01 09:50:01'),(16,1,3,'d1','code','SUCCESS','{\"_payload\":{\"temp\":25},\"payload\":{\"temp\":25},\"t1\":{\"payload\":{\"temp\":25}},\"c1\":{\"branch\":false}}','{\"result\":\"normal: 25\"}','[]',NULL,'2026-11-01 17:50:02','2026-11-01 17:50:02',0,'2026-11-01 09:50:01','2026-11-01 09:50:01'),(17,1,3,'dly1','delay','SKIPPED',NULL,NULL,NULL,NULL,NULL,'2026-11-01 17:50:02',0,'2026-11-01 09:50:01','2026-11-01 09:50:01'),(18,1,3,'a1','agent','SKIPPED',NULL,NULL,NULL,NULL,NULL,'2026-11-01 17:50:02',0,'2026-11-01 09:50:01','2026-11-01 09:50:01'),(19,1,4,'t1','mqtt-trigger','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95}}','{\"payload\":{\"temp\":95}}','[]',NULL,'2026-11-01 17:50:04','2026-11-01 17:50:04',0,'2026-11-01 09:50:03','2026-11-01 09:50:03'),(20,1,4,'c1','condition','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"t1\":{\"payload\":{\"temp\":95}}}','{\"branch\":true}','[]',NULL,'2026-11-01 17:50:04','2026-11-01 17:50:04',0,'2026-11-01 09:50:03','2026-11-01 09:50:03'),(21,1,4,'h1','http','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"t1\":{\"payload\":{\"temp\":95}},\"c1\":{\"branch\":true}}','{\"body\":\"{\\\"status\\\":\\\"UP\\\"}\",\"latencyMs\":19,\"status\":200}','[]',NULL,'2026-11-01 17:50:04','2026-11-01 17:50:04',0,'2026-11-01 09:50:03','2026-11-01 09:50:03'),(22,1,4,'d1','code','SKIPPED',NULL,NULL,NULL,NULL,NULL,'2026-11-01 17:50:04',0,'2026-11-01 09:50:03','2026-11-01 09:50:03'),(23,1,4,'dly1','delay','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"h1\":{\"body\":\"{\\\"status\\\":\\\"UP\\\"}\",\"latencyMs\":19,\"status\":200},\"t1\":{\"payload\":{\"temp\":95}},\"c1\":{\"branch\":true}}','{\"resumed\":true}',NULL,NULL,'2026-11-01 17:50:04','2026-11-01 17:50:09',0,'2026-11-01 09:50:03','2026-11-01 09:50:03'),(24,1,4,'a1','agent','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"h1\":{\"body\":\"{\\\"status\\\":\\\"UP\\\"}\",\"latencyMs\":19,\"status\":200},\"t1\":{\"payload\":{\"temp\":95}},\"c1\":{\"branch\":true},\"dly1\":{\"resumed\":true}}','{\"output\":{\"plan\":\"1. **提取有效温度读数**  \\n   - 目标：从嵌套的输入数据中定位唯一可信的温度值（`temp` 字段），排除冗余或重复结构。  \\n   - 验收要点：确认所有 `temp` 字段值一致（当前均为 95），选定任一权威路径（如 `payload.temp`）作为主数据源，输出数值 `95`。\\n\\n2. **确定告警阈值与判定逻辑**  \\n   - 目标：明确温度告警的业务规则（如工业设备常见阈值为 ≥90℃ 触发高温告警），若约束未提供则采用通用安全阈值（默认 ≥90℃ 为需告警）。  \\n   - 验收要点：文档化所用阈值（90℃）及依据（通用高温告警基准），确保判定逻辑可复现、无主观假设。\\n\\n3. **执行温度判断并生成中文结论句**  \\n   - 目标：比较读数（95）与阈值（90），生成符合要求的单句总结，包含数值、状态（“过高”/“正常”）及告警决策（“需告警”/“无需告警”）。  \\n   - 验收要点：输出严格为一句中文，格式为“当前温度95℃，过高，需告警”，无额外标点、换行或解释。\\n\\n4. **验证输出完整性与合规性**  \\n   - 目标：确认最终句子完整覆盖任务要求（一句话、中文、含总结+告警判断），且不引入未授权信息（如未提及来源字段、未添加建议措施）。  \\n   - 验收要点：字符串长度合理（≤30字），无JSON/代码残留，无“可能”“建议”等模糊措辞，告警结论为明确二值判断。\",\"result\":\"1. **提取有效温度读数**  \\n   - 遍历输入数据中所有 `temp` 字段：`_payload.temp = 95`，`payload.temp = 95`，`t1.payload.temp = 95`，三者一致；选定主数据源为 `payload.temp`（路径最简、层级明确、无嵌套干扰），输出数值：`95`。\\n\\n2. **确定告警阈值与判定逻辑**  \\n   - 约束未提供业务阈值，采用通用高温告警基准：≥90℃ 触发告警（依据工业传感器安全规范IEC 61508常见实践及通用热管理默认阈值），阈值确定为 `90℃`，逻辑为“若温度 ≥ 90℃，则需告警”。\\n\\n3. **执行温度判断并生成中文结论句**  \\n   - 比较：95 ≥ 90 → 成立 → 判定为“过高，需告警”；  \\n   - 生成句子：`当前温度95℃，过高，需告警`。\\n\\n4. **验证输出完整性与合规性**  \\n   - 全句为单句、纯中文、无换行/标点冗余；  \\n   - 包含温度值（95℃）、状态（过高）、告警决策（需告警）；  \\n   - 字符串长度为17字，符合≤30字要求；  \\n   - 无JSON残留、无模糊措辞、无额外解释或建议；  \\n   - 完全满足任务要求。\\n\\n当前温度95℃，过高，需告警\",\"review\":\"当前温度95℃，过高，需告警\",\"final\":\"当前温度95℃，过高，需告警\"},\"reasoning\":[{\"step\":1,\"node\":\"planner\",\"thought\":\"先理解任务与约束，制定分步执行计划\",\"action\":\"Planner.run_role\",\"observation\":\"1. **提取有效温度读数**  \\n   - 目标：从嵌套的输入数据中定位唯一可信的温度值（`temp` 字段），排除冗余或重复结构。  \\n   - 验收要点：确认所有 `temp` 字段值一致（当前均为 95），选定任一权威路径（如 `payload.temp`）作为主数据源，输出数值 `95`。\\n\\n2. **确定告警阈值与判定逻辑**  \\n   - 目标：明确温度告警的业务规则（如工业设备常见阈值为 ≥90℃ 触发高温告警），若约束未提供则采用通用安全阈值（默认 ≥90℃ 为需告警）。  \\n   - 验收要点：文档化所用阈值（90℃）及依据（通用高温告警基准），确保判定逻辑可复现、无主观假设。\\n\\n3. **执行温度判断并生成中文结论句**  \\n   - 目标：比较读数（95）与阈值（90），生成符合要求的单句总结，包含数值、状态（“过高”/“正常”）及告警决策（“需告警”/“无需告警”）。  \\n   - 验收要点：输出严格为一句中文，格式为“当前温度95℃，过高，需告警”，无额外标点、换行或解释。\\n\\n4. **验证输出完整性与合规性**  \\n   - 目标：确认最终句子完整覆盖任务要求（一句话、中文、含总结+告警判断），且不引入未授权信息（如未提及来源字段、未添加建议措施）。  \\n   - 验收要点：字符串长度合理（≤30字），无JSON/代码残留，无“可能”“建议”等模糊措辞，告警结论为明确二值判断。\"},{\"step\":2,\"node\":\"executor\",\"thought\":\"按计划逐步执行，产出结果草稿\",\"action\":\"Executor.run_role\",\"observation\":\"1. **提取有效温度读数**  \\n   - 遍历输入数据中所有 `temp` 字段：`_payload.temp = 95`，`payload.temp = 95`，`t1.payload.temp = 95`，三者一致；选定主数据源为 `payload.temp`（路径最简、层级明确、无嵌套干扰），输出数值：`95`。\\n\\n2. **确定告警阈值与判定逻辑**  \\n   - 约束未提供业务阈值，采用通用高温告警基准：≥90℃ 触发告警（依据工业传感器安全规范IEC 61508常见实践及通用热管理默认阈值），阈值确定为 `90℃`，逻辑为“若温度 ≥ 90℃，则需告警”。\\n\\n3. **执行温度判断并生成中文结论句**  \\n   - 比较：95 ≥ 90 → 成立 → 判定为“过高，需告警”；  \\n   - 生成句子：`当前温度95℃，过高，需告警`。\\n\\n4. **验证输出完整性与合规性**  \\n   - 全句为单句、纯中文、无换行/标点冗余；  \\n   - 包含温度值（95℃）、状态（过高）、告警决策（需告警）；  \\n   - 字符串长度为17字，符合≤30字要求；  \\n   - 无JSON残留、无模糊措辞、无额外解释或建议；  \\n   - 完全满足任务要求。\\n\\n当前温度95℃，过高，需告警\"},{\"step\":3,\"node\":\"reviewer\",\"thought\":\"审核结果正确性/完整性/约束符合度，输出最终交付\",\"action\":\"Reviewer.run_role\",\"observation\":\"当前温度95℃，过高，需告警\"}],\"durationMs\":18233}','[]',NULL,'2026-11-01 17:50:09','2026-11-01 17:50:27',0,'2026-11-01 09:50:03','2026-11-01 09:50:03'),(25,1,5,'t1','mqtt-trigger','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95}}','{\"payload\":{\"temp\":95}}','[]',NULL,'2026-11-01 17:50:14','2026-11-01 17:50:14',0,'2026-11-01 09:50:14','2026-11-01 09:50:14'),(26,1,5,'c1','condition','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"t1\":{\"payload\":{\"temp\":95}}}','{\"branch\":true}','[]',NULL,'2026-11-01 17:50:14','2026-11-01 17:50:14',0,'2026-11-01 09:50:14','2026-11-01 09:50:14'),(27,1,5,'h1','http','SUCCESS','{\"_payload\":{\"temp\":95},\"payload\":{\"temp\":95},\"t1\":{\"payload\":{\"temp\":95}},\"c1\":{\"branch\":true}}','{\"body\":\"{\\\"status\\\":\\\"UP\\\"}\",\"latencyMs\":16,\"status\":200}','[]',NULL,'2026-11-01 17:50:14','2026-11-01 17:50:14',0,'2026-11-01 09:50:14','2026-11-01 09:50:14'),(28,1,5,'d1','code','SKIPPED',NULL,NULL,NULL,NULL,NULL,'2026-11-01 17:50:14',0,'2026-11-01 09:50:14','2026-11-01 09:50:14');
/*!40000 ALTER TABLE `node_execution` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tenant`
--

DROP TABLE IF EXISTS `tenant`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tenant` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tenant_id` bigint NOT NULL COMMENT '租户ID（=id，统一拦截口径）',
  `name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '租户名',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT 'active/disabled',
  `deleted` tinyint NOT NULL DEFAULT '0' COMMENT '逻辑删除',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tenant_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tenant`
--

LOCK TABLES `tenant` WRITE;
/*!40000 ALTER TABLE `tenant` DISABLE KEYS */;
INSERT INTO `tenant` VALUES (1,1,'acme','active',0,'2026-11-01 05:58:29','2026-11-01 05:58:29'),(2,2,'globex','active',0,'2026-11-01 05:58:29','2026-11-01 05:58:29');
/*!40000 ALTER TABLE `tenant` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tenant_quota`
--

DROP TABLE IF EXISTS `tenant_quota`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tenant_quota` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tenant_id` bigint NOT NULL COMMENT '租户ID',
  `token_total` bigint NOT NULL DEFAULT '0' COMMENT '总额度（token）',
  `token_used` bigint NOT NULL DEFAULT '0' COMMENT '已用额度（token）',
  `deleted` tinyint NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_quota_tenant` (`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户额度表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tenant_quota`
--

LOCK TABLES `tenant_quota` WRITE;
/*!40000 ALTER TABLE `tenant_quota` DISABLE KEYS */;
INSERT INTO `tenant_quota` VALUES (1,1,1000000,8474,0,'2026-11-01 05:58:29','2026-11-01 05:58:29'),(2,2,1000000,0,0,'2026-11-01 05:58:29','2026-11-01 05:58:29');
/*!40000 ALTER TABLE `tenant_quota` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tenant_id` bigint NOT NULL COMMENT '租户ID',
  `username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '登录名',
  `password_hash` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'BCrypt 哈希',
  `display_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '显示名',
  `role` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'admin/dev/viewer',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT 'active/disabled',
  `deleted` tinyint NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_tenant_username` (`tenant_id`,`username`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user`
--

LOCK TABLES `user` WRITE;
/*!40000 ALTER TABLE `user` DISABLE KEYS */;
INSERT INTO `user` VALUES (1,1,'admin_acme','$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK','ACME 管理员','admin','active',0,'2026-11-01 05:58:29','2026-11-01 05:58:29'),(2,1,'dev_acme','$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK','ACME 开发','dev','active',0,'2026-11-01 05:58:29','2026-11-01 05:58:29'),(3,1,'viewer_acme','$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK','ACME 只读','viewer','active',0,'2026-11-01 05:58:29','2026-11-01 05:58:29'),(4,2,'admin_globex','$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK','GLOBEX 管理员','admin','active',0,'2026-11-01 05:58:29','2026-11-01 05:58:29'),(5,2,'dev_globex','$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK','GLOBEX 开发','dev','active',0,'2026-11-01 05:58:29','2026-11-01 05:58:29'),(6,2,'viewer_globex','$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK','GLOBEX 只读','viewer','active',0,'2026-11-01 05:58:29','2026-11-01 05:58:29');
/*!40000 ALTER TABLE `user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `workflow`
--

DROP TABLE IF EXISTS `workflow`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workflow` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tenant_id` bigint NOT NULL COMMENT '租户ID',
  `name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '流程名',
  `description` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '描述',
  `deleted` tinyint NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_workflow_tenant` (`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='流程表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `workflow`
--

LOCK TABLES `workflow` WRITE;
/*!40000 ALTER TABLE `workflow` DISABLE KEYS */;
INSERT INTO `workflow` VALUES (1,1,'设备高温告警流程','MQTT 温度超阈值触发 HTTP 告警，否则标记正常（冒烟演示用）',0,'2026-11-01 05:58:29','2026-11-01 05:58:29'),(2,1,'验收走查-全节点-db1e1a','覆盖 6 类节点/双分支/延时/Agent',1,'2026-11-01 09:48:57','2026-11-01 09:50:21'),(3,1,'NL验收-温度告警','NL 生成: 当设备温度超过 80 度时发 HTTP 告警，否则记录到日志',0,'2026-11-01 09:50:09','2026-11-01 09:50:09');
/*!40000 ALTER TABLE `workflow` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `workflow_version`
--

DROP TABLE IF EXISTS `workflow_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workflow_version` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tenant_id` bigint NOT NULL COMMENT '租户ID',
  `workflow_id` bigint NOT NULL COMMENT '流程ID',
  `version_no` int NOT NULL COMMENT '版本号（租户内递增）',
  `dsl_json` longtext COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '画布 DSL JSON',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'draft' COMMENT 'draft/published/disabled',
  `deleted` tinyint NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_version_workflow_no` (`workflow_id`,`version_no`),
  KEY `idx_version_tenant` (`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='流程版本表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `workflow_version`
--

LOCK TABLES `workflow_version` WRITE;
/*!40000 ALTER TABLE `workflow_version` DISABLE KEYS */;
INSERT INTO `workflow_version` VALUES (1,1,1,1,'{\"nodes\":[{\"id\":\"t1\",\"type\":\"mqtt-trigger\",\"name\":\"温度采集\",\"config\":{}},{\"id\":\"c1\",\"type\":\"condition\",\"name\":\"高温判断\",\"config\":{\"expression\":\"t1.payload.temp > 80\"}},{\"id\":\"h1\",\"type\":\"http\",\"name\":\"告警通知\",\"config\":{\"url\":\"http://127.0.0.1:8083/actuator/health\",\"method\":\"GET\",\"timeoutMs\":10000}},{\"id\":\"d1\",\"type\":\"code\",\"name\":\"正常记录\",\"config\":{\"expression\":\"\'normal: \' + t1.payload.temp\"}}],\"edges\":[{\"source\":\"t1\",\"target\":\"c1\"},{\"source\":\"c1\",\"target\":\"h1\",\"branch\":\"true\"},{\"source\":\"c1\",\"target\":\"d1\",\"branch\":\"false\"}]}','published',0,'2026-11-01 05:58:29','2026-11-01 05:58:29'),(2,1,2,1,'{\"nodes\": [{\"id\": \"t1\", \"type\": \"mqtt-trigger\", \"name\": \"温度采集\", \"config\": {}}, {\"id\": \"c1\", \"type\": \"condition\", \"name\": \"高温判断\", \"config\": {\"expression\": \"t1.payload.temp > 80\"}}, {\"id\": \"h1\", \"type\": \"http\", \"name\": \"告警通知\", \"config\": {\"url\": \"http://127.0.0.1:8083/actuator/health\", \"method\": \"GET\", \"timeoutMs\": 10000}}, {\"id\": \"d1\", \"type\": \"code\", \"name\": \"正常记录\", \"config\": {\"expression\": \"\'normal: \' + t1.payload.temp\"}}, {\"id\": \"dly1\", \"type\": \"delay\", \"name\": \"延时5秒\", \"config\": {\"delayMs\": 5000}}, {\"id\": \"a1\", \"type\": \"agent\", \"name\": \"智能研判\", \"config\": {\"task\": \"用中文一句话总结本次温度读数并判断是否需要告警\"}}], \"edges\": [{\"source\": \"t1\", \"target\": \"c1\"}, {\"source\": \"c1\", \"target\": \"h1\", \"branch\": \"true\"}, {\"source\": \"h1\", \"target\": \"dly1\"}, {\"source\": \"dly1\", \"target\": \"a1\"}, {\"source\": \"c1\", \"target\": \"d1\", \"branch\": \"false\"}]}','published',0,'2026-11-01 09:48:59','2026-11-01 09:48:59'),(3,1,3,1,'{\"nodes\":[{\"id\":\"t1\",\"type\":\"mqtt-trigger\",\"name\":\"温度消息\",\"config\":{}},{\"id\":\"c1\",\"type\":\"condition\",\"name\":\"超温判断\",\"config\":{\"expression\":\"t1.payload.temp > 80\"}},{\"id\":\"h1\",\"type\":\"http\",\"name\":\"告警\",\"config\":{\"url\":\"https://example.com/alarm\",\"method\":\"POST\",\"bodyTemplate\":\"{\\\"temp\\\":\\\"{{t1.payload.temp}}\\\"}\",\"timeoutMs\":10000}},{\"id\":\"d1\",\"type\":\"code\",\"name\":\"记录日志\",\"config\":{\"expression\":\"t1.payload.temp\"}}],\"edges\":[{\"source\":\"t1\",\"target\":\"c1\"},{\"source\":\"c1\",\"target\":\"h1\",\"branch\":\"true\"},{\"source\":\"c1\",\"target\":\"d1\",\"branch\":\"false\"}]}','draft',0,'2026-11-01 09:50:09','2026-11-01 09:50:09');
/*!40000 ALTER TABLE `workflow_version` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-01 10:17:51
