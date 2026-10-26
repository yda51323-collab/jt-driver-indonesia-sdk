# -*- coding: utf-8 -*-
"""JT-Driver-Indonesia 配送域 SDK（印尼区域）。

封装派单轮询、取件扫码、妥投回传、离线补传队列。
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

__version__ = "1.6.2"

SERVICE_ID = "JT-Driver-Indonesia"
REGISTRY_KEY = "jt-driver-indonesia"
API_VERSION = "v2"
REGION = "ID"
DEFAULT_GATEWAY = "https://gw.jt-driver-indonesia.example.com"
ENV_KEY = "JT_DRIVER_KEY"

POLL_INTERVAL_S = 5
POLL_TIMEOUT_S = 25
MAX_OFFLINE_BATCH = 200


@dataclass
class RetryPolicy:
    max_attempts: int = 4
    backoff_ms: int = 300
    max_backoff_ms: int = 5000

    def delay(self, attempt: int) -> float:
        step = self.backoff_ms * (2 ** max(attempt - 1, 0))
        return min(step, self.max_backoff_ms) / 1000.0


@dataclass
class Task:
    task_no: str
    scan_code: str
    window_start: int
    window_end: int
    replay: bool = False

    @property
    def window_minutes(self) -> int:
        return max((self.window_end - self.window_start) // 60, 0)


class DriverClient:
    """骑手端配送客户端。transport 由宿主 App 注入。"""

    def __init__(self, courier_id: str, app_key: str = "", region: str = REGION,
                 transport: Any = None) -> None:
        self.courier_id = courier_id
        self.app_key = app_key or os.environ.get(ENV_KEY, "")
        self.region = region.upper()
        self.transport = transport
        self.retry = RetryPolicy()
        if not self.app_key:
            raise ValueError("app_key 缺失，检查环境变量 %s" % ENV_KEY)

    def _path(self, suffix: str) -> str:
        return "/openapi/%s/%s%s" % (API_VERSION, REGISTRY_KEY, suffix)

    def poll_pending(self, limit: int = 20) -> List[Task]:
        """拉取待取件派单。长轮询超过 POLL_TIMEOUT_S 由客户端主动断开。"""
        payload = {
            "courier_id": self.courier_id,
            "region": self.region,
            "limit": min(limit, MAX_OFFLINE_BATCH),
            "wait": POLL_TIMEOUT_S,
        }
        resp = self.transport.post(self._path("/task/pending"), payload)
        return [Task(**row) for row in resp.get("tasks", [])]

    def mark_picked(self, task_no: str, scan_code: str) -> bool:
        resp = self.transport.post(self._path("/task/picked"), {
            "courier_id": self.courier_id,
            "task_no": task_no,
            "scan_code": scan_code,
            "ts": int(time.time()),
        })
        return bool(resp.get("ok"))

    def flush_offline(self, queued: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        """离线队列补传。服务端按 replay=True 只做幂等校验。"""
        batch = list(queued)[:MAX_OFFLINE_BATCH]
        for row in batch:
            row["replay"] = True
        return self.transport.post(self._path("/task/replay"), {"items": batch})
