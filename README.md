# SaaS 工作流编排平台（saas-workflow-agent）

[![CI](https://github.com/OWNER/REPO/actions/workflows/test.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/test.yml)

> badge 中 `OWNER/REPO` 为占位符。本项目当前位于 `ai-dev-workflow` 仓库的 `projects/saas-workflow-agent` 子目录；作为独立仓库发布时，把 `.github/workflows/test.yml` 放到仓库根目录并替换 `OWNER/REPO`。

技术栈：Spring Boot 3（Java 8083）+ Vue 3 / Vite（5177）+ FastAPI / LangGraph（python-agent 8085）+ MySQL 3310 + Redis 6379 + RabbitMQ + Mosquitto。

## 目录

| 目录 | 内容 |
|---|---|
| `05_代码/` | 后端、前端、python-agent、`docker-compose.yml`、`db/init.sql` |
| `06_冒烟/` `07_联调/` | 冒烟与全链路联调记录、脚本、证据 |
| `08_测试/` | pytest 四层框架（`qa-automation/`）、M5 评审、性能报告、Allure |
| `08.5_安全扫描/` | 安全扫描报告 |
| `09_验收/` `10_交付/` | 验收与交付产物 |

## 测试

```bash
cd 08_测试/qa-automation
python -m pytest -q                                   # 全量（需本地服务与中间件就绪）
python -m pytest --collect-only -q                    # CI 用例收集（不连库）
python perf_test.py                                   # 三档并发轻量压测
npx allure-commandline generate reports/allure-results -o reports/allure-report --clean
```

测试结果与文档见 `08_测试/第一轮测试报告.md`、`08_测试/基线指标验证表.md`、`08_测试/全量测试用例清单.md`。
