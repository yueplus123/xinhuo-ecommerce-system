# 微信机器人 → 薪火「微信BOT数据」对接说明

## 数据流

```
微信群消息 → 普通微信记账机器人记账成功
  → POST 薪火 /api/external/wechat-bot/push/
  → 入库 WechatBotRecord
  → 职员端「微信BOT数据」按业务 Tab 展示（页内人员筛选）
```

## 账本映射

| 机器人 `book` / 别名 | 薪火表 `table_type` | 页面 Tab |
|----------------------|---------------------|----------|
| `recharge` / 充币 | `pixivcoban` | 充币 |
| `once_card` / 一次卡 | `once_card` | 一次卡 |
| `shared` / 共享 | `shared` | 共享 |
| `package` / 打包 | `package` | 打包 |
| `openrouter` / op / plus | `openrouter` | openrouter |
| `patreon` / pat | `patreon` | patreon |
| `commission` / 约稿 | `commission` | 约稿 |
| `booth` | `booth` | booth |
| `pictspace` / pict | `pictspace` | pictspace |
| `premium` / 高级会员 | `premium` | 高级会员 |
| `mega` | `mega` | mega |
| `gpt_recharge` / gpt | `chatgpt` | gpt |
| `usdt` | `usdt` | USDT |

普通记账（`ledger`）**不推送本页**；仅业务名含 gpt/代充时归入 gpt 表。

## 薪火侧配置

```bash
EXTERNAL_PUSH_API_KEY=双方约定的密钥
# 可选默认职员（收款推送用；BOT 业务表不依赖）
EXTERNAL_PUSH_DEFAULT_USERNAME=admin
```

接口：

- 推送：`POST /api/external/wechat-bot/push/`（Header `X-Api-Key`）
- 拉取：`POST /api/external/wechat-bot/push/` + `{"action":"pull","status":"ACTIVE","employee_name":"张超","business_name":"充币"}`（均可选）
- 探测：`GET /api/external/wechat-bot/push/`
- 职员列表：`GET /api/wechat-bot/records/?table=<table_type>&employee=&q=&page=`
- 人员筛选项：`GET /api/wechat-bot/employees/?table=<table_type>`

## 机器人侧配置（`config/.env`）

```bash
XINHUO_API_BASE=http://192.144.236.133
XINHUO_BOT_PUSH_URL=http://192.144.236.133/api/external/wechat-bot/push/
XINHUO_BOT_PUSH_API_KEY=与薪火 EXTERNAL_PUSH_API_KEY 相同
XINHUO_BOT_PUSH_TIMEOUT=8
```

实现位置：

- 推送模块：`apps/integrations/xinhuo_push.py`
- 挂钩：`apps/gateway_api/services.py` 在记账/记单/USDT 成功后 `schedule_push_ledger_entry`
  - `book=ledger` → 记账系统
  - `book=staff_order` / `usdt` → 本页（微信BOT数据）
- 清空：记单「清空业务-姓名」、USDT「已转账」→ `action=status` 更新为已清空
- 使用 `transaction.on_commit`，避免回滚脏推

## 幂等

`event_id = wxbot-{MessageEvent.event_uuid}`。同一事件重复 POST 返回 `duplicate`，不重复入库。

## 状态更新

```json
{
  "action": "status",
  "event_id": "wxbot-a1b2c3d4",
  "status": "PROCESSED"
}
```

## 单条推送示例

```json
{
  "event_id": "wxbot-a1b2c3d4",
  "book": "充币",
  "quantity": 1,
  "employee_name": "张越",
  "chat_name": "记单群",
  "occurred_at": "2026-09-15T11:00:00+08:00",
  "status": "ACTIVE"
}
```

USDT 示例：

```json
{
  "event_id": "wxbot-a1b2c3d4",
  "table_type": "usdt",
  "book": "usdt",
  "amount_cny": "6740",
  "amount_usd": "2000",
  "employee_name": "张越",
  "occurred_at": "2026-09-15T11:00:00+08:00",
  "status": "ACTIVE"
}
```

## 联调步骤

1. 薪火：`migrate`，配置 `EXTERNAL_PUSH_API_KEY`，启动后端
2. 机器人：`config/.env` 中 `XINHUO_API_BASE` / `XINHUO_BOT_PUSH_API_KEY` 与薪火一致，重启听群
3. 群内发 `充币+1` / `给我6740，2000刀` / `一个月+1`
4. 打开薪火「微信BOT数据」对应 Tab，点刷新应能看到记录
5. 发 `清空充币-张越` 或 `已转账` 后，页上「清空状态」应变为已清空
