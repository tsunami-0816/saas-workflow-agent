# swa-frontend · SaaS 工作流编排平台前端

[![CI](https://github.com/OWNER/REPO/actions/workflows/test.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/test.yml)

> badge 中的 `OWNER/REPO` 为占位符，推送到 GitHub 后替换为实际仓库路径。

Vue 3.4 + Vite 5.2 + TypeScript + Element Plus 2.7 + AntV X6 2.18 + Pinia。端口 **5177**。

## 安装与启动

```bash
npm install
npm run dev        # 开发（默认启用 Mock，见下）
npm run build      # 产物构建（vue-tsc 类型检查 + vite build）
```

## Mock 开关（INF-3）

由环境变量 `VITE_USE_MOCK` 控制，**无需改代码**：

| 文件 | 取值 | 说明 |
|---|---|---|
| `.env.development` | `VITE_USE_MOCK=true` | 本地 Mock：axios 自定义 adapter 按《接口文档.md》路由/字段/错误码应答，含执行过程定时器模拟与 SSE 模拟；种子账号 admin_acme / dev_acme / viewer_acme，密码 `Swa@123456` |
| `.env.production` | `VITE_USE_MOCK=false` | 真实后端：请求经 vite dev proxy `/api` → `http://localhost:8083` |

切真实后端联调：把 `.env.development` 改为 `VITE_USE_MOCK=false` 并启动 java-backend(:8083) 即可。

## 目录结构

```
src/
├── api/            # axios 封装（统一壳/超时/401 跳登录）+ 各域接口
├── mock/           # INF-3 Mock 层：db(种子) / runtime(执行+SSE 模拟) / index(adapter)
├── stores/auth.ts  # JWT + 当前用户（localStorage）
├── router/         # 路由守卫（未登录跳登录；审计页仅 admin）
├── layouts/        # 主布局（按角色过滤菜单）
├── views/          # 登录 / 流程列表 / 画布编辑器 / 执行列表 / 执行详情(SSE) / MQTT / 额度计量 / 审计
├── components/     # 节点配置面板 / 版本管理抽屉 / NL 草稿对话框
└── utils/          # dsl(序列化+校验) / sse(fetch 流式+断线快照续订) / format
```

## 关键设计

- **租户**：tenantId 一律由后端 JWT claim 决定，前端不传。
- **RBAC**：viewer 菜单/按钮隐藏（写入口全隐），越权由服务端 403 兜底。
- **画布**：6 类节点 HTML5 拖拽入画布；连线约束（触发器无入边/禁重边/禁成环）即时提示；条件分支出边自动标 true/false（双击切换）；DSL 严格对齐后端 DslDocument（坐标只存 localStorage，不进 DSL）；未保存离开双提示（路由 + beforeunload）。
- **SSE**：后端仅认 Authorization 头，故用 fetch 流式解析 text/event-stream；断线先拉 `/executions/{id}/nodes` 快照再指数退避续订；执行终态主动断开。Mock 模式走内存模拟器。
- **XSS**：节点输入/输出等用户内容一律文本转义展示，禁用 v-html。
