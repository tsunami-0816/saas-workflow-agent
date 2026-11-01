"""M5 基线指标取样脚本：自然语言 → 流程草稿（真实 DashScope 千问调用）。

用途：一次跑完 20 条需求，落盘「输入 / 生成 DSL / 节点类型 / 连线数」原始证据，
供 `M5_自然语言转流程评审.md` 逐条人工评审（结构合法 + 语义基本符合）。

用法（在 08_测试/qa-automation 目录下）：
    python ..\\M5\\m5_nl_eval.py

约定：
1. 每条需求独立请求 `POST /api/v1/workflows/nl-draft`，成功后立即删除生成的流程，避免污染 8/9 步数据；
2. 只记录原始输出，不在脚本里做语义打分（语义评审必须人工/评审人逐条判断，避免自评自过）；
3. 结果写 `08_测试/M5/m5_results.json`。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_QA_ROOT = Path(__file__).resolve().parents[1] / "qa-automation"
sys.path.insert(0, str(_QA_ROOT))

from common.request_util import ApiClient, login  # noqa: E402

BASE = "http://localhost:8083"
USERNAME = "dev_acme"
PASSWORD = "Swa@123456"

SAMPLES = [
    "设备上报温度，超过 80 度调用告警接口，否则记录一条正常日志",
    "收到订单消息后先等待 5 秒，再调用库存扣减接口，库存不足就记录错误",
    "每分钟检查一次服务健康状态，健康则继续，异常则调用告警回调",
    "先调用 A 接口获取用户信息，再调用 B 接口拉取订单，最后让智能排查订单异常原因",
    "设备离线超过 10 分钟就发通知给运维，未超过则忽略",
    "收到支付成功消息后，先调用发票服务，然后延时 2 秒再推送消息给客户",
    "采集到的电压低于 200 时触发降压告警，高于 240 时触发过压告警，其余情况记录",
    "用户注册完成后，调用短信服务发送欢迎短信，失败重试",
    "先调用天气接口，温度低于 5 度就调用供暖控制接口，否则记录温度",
    "订单金额大于 1000 元走人工审核接口，否则自动通过",
    "收到传感器数据后，让智能体分析是否需要维修，需要则调用派单接口",
    "设备上报湿度，超过 90 调用除湿机接口，30 到 90 之间记录数据",
    "每天定时拉取销售数据，拉取失败则等待 10 秒后重试",
    "收到告警消息，先智能体判断严重程度，严重则电话告警，否则发邮件",
    "调用设备状态接口，返回离线则调用重启接口",
    "先等待 3 秒，再调用外部接口提交工单，提交成功后记录工单号",
    "收到消息后判断等级是否为 P0，是则立即调用电话告警接口，否则记录",
    "拉取库存接口，库存小于 10 调用补货接口，否则记录库存",
    "把设备上报的数据交给智能体做异常诊断，输出诊断报告",
    "先调用登录校验接口，失败则直接结束，成功则继续调用数据查询接口",
]


def main() -> int:
    body = login(BASE, USERNAME, PASSWORD)
    token = body["data"]["token"]
    client = ApiClient(BASE, token, timeout=120)
    rows: list[dict] = []
    ok = 0
    try:
        for idx, text in enumerate(SAMPLES, start=1):
            name = f"M5-{idx:02d}-{int(time.time() * 1000)}"
            started = time.time()
            resp = client.post("/api/v1/workflows/nl-draft",
                               json={"text": text, "workflowName": name})
            elapsed = round(time.time() - started, 2)
            payload = resp.json()
            row = {"index": idx, "text": text, "elapsedSec": elapsed,
                   "httpStatus": resp.status_code, "code": payload.get("code"),
                   "message": payload.get("message")}
            if payload.get("code") == 0:
                ver = payload["data"]
                dsl = json.loads(ver["dslJson"])
                row["nodes"] = [{"id": n["id"], "type": n["type"], "name": n["name"]} for n in dsl["nodes"]]
                row["edges"] = dsl["edges"]
                row["nodeCount"] = len(dsl["nodes"])
                row["edgeCount"] = len(dsl["edges"])
                row["dslJson"] = ver["dslJson"]
                ok += 1
                client.delete(f"/api/v1/workflows/{ver['workflowId']}")
            else:
                row["body"] = json.dumps(payload, ensure_ascii=False)[:500]
            rows.append(row)
            print(f"[M5] {idx:02d} code={row['code']} nodes={row.get('nodeCount')} "
                  f"edges={row.get('edgeCount')} {elapsed}s")
    finally:
        client.close()

    out = Path(__file__).resolve().parent / "m5_results.json"
    out.write_text(json.dumps({"generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
                               "success": ok, "total": len(SAMPLES), "rows": rows},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完成：生成成功 {ok}/{len(SAMPLES)}，证据落盘 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
