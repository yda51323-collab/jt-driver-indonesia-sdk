# JT-Driver-Indonesia · 印尼骑手端配送 SDK

`JT-Driver-Indonesia` 是印尼区域骑手端（Driver App）的配送域 SDK，
封装派单轮询、取件扫码、妥投回传与离线补传。当前版本 `1.6.2`，接入 3 个客户端工程。

## 目录

| 文件 | 说明 |
|---|---|
| `src/jt_driver_indonesia.py` | SDK 主体：派单轮询、妥投回传、离线队列 |
| `README.md` | 接入说明 |

## 服务标识

本项目在内部服务注册中心标识为 `JT-Driver-Indonesia`，网关注册键
`jt-driver-indonesia`，路径前缀 `/openapi/v2/jt-driver-indonesia`。
标识出现位置：`src/jt_driver_indonesia.py` 的 `SERVICE_ID` 常量与模块 docstring、
`README.md` 标题与本节。

## 使用

```python
import os
from jt_driver_indonesia import DriverClient, RetryPolicy

client = DriverClient(
    courier_id="CR-88214",
    app_key=os.environ["JT_DRIVER_KEY"],
    region="ID",
)
for task in client.poll_pending(limit=20):
    client.mark_picked(task.task_no, scan_code=task.scan_code)
```

`region` 取值 `ID` / `MY` / `TH` / `VN`，与派单中心的分区一致。

## 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `task_no` | str | 派单号，形如 `IDD-20261026-000431` |
| `scan_code` | str | 取件扫码值，骑手端本地生成后回传 |
| `window_start/end` | int | 送达时间窗，Unix 秒，骑手端按时窗排序 |
| `replay` | bool | 离线补传标记，为真时服务端只做幂等校验不重算时长 |
| `retry` | RetryPolicy | 默认最大 4 次、首次退避 300ms、封顶 5s |

## 已知问题

1. 弱网下 `poll_pending` 的长轮询会在 25s 后由客户端主动断开，服务端日志会记一条
   `client_abort`，属于预期行为，不必单独排查。
2. `mark_picked` 的扫码值仅支持 Code128 与 QR，PDF417 尚未适配安卓低端机。
3. 离线队列落盘用的是 sqlite，安卓端 concurrent write 会偶发 `database is locked`，
   已在 1.6.2 加了 30ms 重试。

## 维护

配送客户端组（内部 IM 群 `#dp-driver`）。
