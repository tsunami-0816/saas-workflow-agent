-- 2026-10-31 修复种子流程 v1（workflow_version id=1）两处缺陷：
-- 1) code 节点 d1 配置键 script → expression（执行器读 config.expression）
-- 2) http 节点 h1 外网 example.com → 本机健康检查（避免走查时网络失败误判）
UPDATE workflow_version
SET dsl_json = '{"nodes":[{"id":"t1","type":"mqtt-trigger","name":"温度采集","config":{}},{"id":"c1","type":"condition","name":"高温判断","config":{"expression":"t1.payload.temp > 80"}},{"id":"h1","type":"http","name":"告警通知","config":{"url":"http://127.0.0.1:8083/actuator/health","method":"GET","timeoutMs":10000}},{"id":"d1","type":"code","name":"正常记录","config":{"expression":"''normal: '' + t1.payload.temp"}}],"edges":[{"source":"t1","target":"c1"},{"source":"c1","target":"h1","branch":"true"},{"source":"c1","target":"d1","branch":"false"}]}',
    updated_at = NOW()
WHERE id = 1 AND tenant_id = 1;

SELECT id, status, LEFT(dsl_json, 260) AS dsl_head FROM workflow_version WHERE id = 1;
