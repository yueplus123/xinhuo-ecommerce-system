# xinhuo-bridge（微信机器人 ↔ 薪火）

对外能力由机器人侧 `xinhuo-bridge` 按固定路径调用，薪火只提供这些接口。

## 能力表

| 能力 | 方法 | 路径 | 鉴权 |
|------|------|------|------|
| product_query | GET | `/api/external/wechat-bot/products/` | `X-Api-Key` |
| bot_record_push | POST | `/api/external/wechat-bot/push/` | `X-Api-Key` |
| ledger_push | POST | `/api/external/ledger/push/` | `X-Api-Key` |
| bridge_health | GET | `/api/external/bridge/health/` | `X-Api-Key` |

Key 与 `EXTERNAL_PUSH_API_KEY` / `XINHUO_BOT_PUSH_API_KEY` 一致。

## 健康检查

```bash
curl -s -H "X-Api-Key: YOUR_KEY" http://192.144.236.133/api/external/bridge/health/
```

返回 `ok`、能力列表。机器人桌面「薪火对接 → 测试连接」会优先打此接口。

## 幂等

`bot_record_push` / `ledger_push` 请求体含 `event_id`，重复推送不产生重复行。

## 机器人配置

```bash
XINHUO_API_BASE=http://192.144.236.133
XINHUO_BOT_PUSH_API_KEY=<同 EXTERNAL_PUSH_API_KEY>
```

详见机器人仓库 `docs/XINHUO_PUSH.md`。
