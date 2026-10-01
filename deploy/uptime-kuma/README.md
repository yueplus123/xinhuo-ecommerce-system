# 服务监控（Uptime Kuma）

薪火侧栏「服务监控」嵌入本服务，用于探测网站 / API / 关键词（模板页）是否存活。

## 启动

```bash
cd deploy/uptime-kuma
docker compose up -d
```

打开：http://127.0.0.1:3001/  
首次进入创建管理员账号，再添加监控项（HTTP / 关键词 / JSON / TCP 等）。

## 停止

```bash
docker compose down
```

## 与薪火的关系

- **探活引擎**：Uptime Kuma（本目录）
- **入口**：薪火前端「服务监控」+ 后台「服务监控页面管理」配置嵌入地址
- 生产环境把 `share_url` 改成你的 Kuma 域名即可
