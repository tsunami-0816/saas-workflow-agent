"""轻量多线程压测：三档并发 10 / 20 / 50，每档 10 秒，压核心读接口。

用法：
    .venv\\Scripts\\python.exe perf_test.py            # 默认压 GET /api/v1/workflows
    .venv\\Scripts\\python.exe perf_test.py --target login
"""
from __future__ import annotations

import argparse
import os
import statistics
import threading
import time

import httpx

BASE = os.environ.get("SWA_BASE", "http://localhost:8083")
PASSWORD = os.environ.get("SWA_TEST_PASSWORD", "Swa@123456")
CONCURRENCIES = (10, 20, 50)
DURATION = 10.0


def _token(username: str) -> str:
    with httpx.Client(base_url=BASE, timeout=10) as c:
        r = c.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        return r.json()["data"]["token"]


def _worker(client: httpx.Client, path: str, deadline: float, out: list, errors: list) -> None:
    while time.monotonic() < deadline:
        t0 = time.perf_counter()
        try:
            r = client.get(path)
            if r.status_code != 200 or r.json().get("code") != 0:
                errors.append(r.status_code)
            else:
                out.append((time.perf_counter() - t0) * 1000)
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc)[:60])


def run(concurrency: int, path: str, token: str) -> dict:
    lat: list[float] = []
    errors: list = []
    clients = [httpx.Client(base_url=BASE, timeout=10,
                            headers={"Authorization": f"Bearer {token}"}) for _ in range(concurrency)]
    # 计时窗口必须在 client 创建完成后再开启，否则高并发下初始化耗时会吃掉压测时长
    start = time.monotonic()
    deadline = start + DURATION
    threads = [threading.Thread(target=_worker, args=(c, path, deadline, lat, errors)) for c in clients]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - start
    for c in clients:
        c.close()

    total = len(lat) + len(errors)
    lat.sort()
    p95 = lat[max(0, int(round(0.95 * len(lat))) - 1)] if lat else 0
    return {
        "concurrency": concurrency,
        "requests": total,
        "tps": round(total / elapsed, 1) if elapsed > 0 else 0,
        "avg_ms": round(statistics.mean(lat), 1) if lat else 0,
        "p95_ms": round(p95, 1),
        "error_rate": round(len(errors) / total, 4) if total else 0,
        "errors_sample": errors[:3],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="workflows", choices=["workflows", "login"])
    args = ap.parse_args()

    if args.target == "login":
        path = "/api/v1/auth/login"
        token = ""
    else:
        path = "/api/v1/workflows?pageNo=1&pageSize=20"
        token = _token("dev_acme")

    print(f"压测目标: GET {path}  BASE={BASE}  DURATION={DURATION}s\n")
    print("| 并发 | 请求数 | TPS | 平均RT(ms) | P95(ms) | 错误率 |")
    print("|---|---|---|---|---|---|")
    rows = []
    for c in CONCURRENCIES:
        r = run(c, path, token)
        rows.append(r)
        print(f"| {r['concurrency']} | {r['requests']} | {r['tps']} | {r['avg_ms']} | {r['p95_ms']} | {r['error_rate']:.2%} |")
    print("\n原始数据:", rows)


if __name__ == "__main__":
    main()
