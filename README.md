# saas-workflow-agent

SaaS自动化工作流集成平台，可视化画布编排业务流程，多Agent协作执行。

## 技术栈
- 后端：Java 17 + Spring Boot 3 + JPA + MySQL + Redis
- Agent：Python FastAPI
- 前端：Vue3 + Element Plus + AntV X6
- 部署：Docker Compose

## 功能
- 工作流画布拖拽编排
- DAG流程执行引擎
- 多Agent协作（CrewAI三角色）
- 模型路由与Token成本管理
- SSE实时执行进度

## 启动
```bash
cd 05_代码
docker compose up -d
# 首次手动建库：docker exec <mysql> mysql -uroot -proot123 -e "CREATE DATABASE workflow;"
cd backend && mvn spring-boot:run
```
