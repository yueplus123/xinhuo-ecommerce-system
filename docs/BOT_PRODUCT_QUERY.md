# BOT 查商品（微信机器人 → 薪火平台商品）

## 能力

群里发「查商品」或「查商品 关键词」，机器人向薪火拉取**在售**商品目录。

返回字段**仅有**：

| 字段 | 含义 |
|------|------|
| `platform_name` | 平台名 |
| `product_name` | 商品名（SKU 名） |

不含价格、图片、教程、话术等其它字段。

## 接口

```
GET  /api/external/wechat-bot/products/
POST /api/external/wechat-bot/products/
```

鉴权：Header `X-Api-Key`（与 `EXTERNAL_PUSH_API_KEY` 相同）。

### Query / Body 参数

| 参数 | 说明 |
|------|------|
| `q` / `keyword` | 关键词（匹配平台名 / 业务名 / 商品名） |
| `platform` | 按平台名模糊过滤 |
| `limit` | 最多条数，默认 50，最大 200 |
| `on_sale` | 默认 `1` 只返回在售；`0` 含全部状态 |
| `as` / `reply` | 传 `text` 时额外返回群聊可读 `text` 字段（勿用 `format=`，会与 DRF 冲突） |

### JSON 示例

```json
{
  "ok": true,
  "count": 2,
  "q": "会员",
  "platform": "",
  "results": [
    {"platform_name": "BOT演示-Patreon", "product_name": "会员月卡"},
    {"platform_name": "BOT演示-Patreon", "product_name": "会员年卡"}
  ]
}
```

### curl 测试

```bash
# 全部（前 50 条在售）
curl -s -H "X-Api-Key: YOUR_KEY" "http://127.0.0.1:8001/api/external/wechat-bot/products/"

# 关键词
curl -s -H "X-Api-Key: YOUR_KEY" "http://127.0.0.1:8001/api/external/wechat-bot/products/?q=会员"

# 群聊文本格式
curl -s -H "X-Api-Key: YOUR_KEY" "http://127.0.0.1:8001/api/external/wechat-bot/products/?q=Fanbox&as=text"
```

## 写入测试数据

```bash
cd django-jazzmin-main
# 需 PYTHONPATH / venv 与本地启动一致
python backend/manage.py seed_bot_product_demo
```

会创建前缀为 `BOT演示-` 的平台与商品（可重复执行，默认先删再写）。

## 机器人侧

- 指令：`查商品` / `查商品 关键词` / `查询商品 xxx`
- 配置沿用 `XINHUO_BOT_PUSH_API_KEY`；商品 URL 可由推送地址推导为  
  `.../api/external/wechat-bot/products/`  
  或单独设 `XINHUO_PRODUCT_QUERY_URL`
