# Django + DRF + Vue3 子域部署说明

## 目标拓扑

- 前端：`app.example.com`（Vue3 静态资源）
- 后端：`api.example.com`（Django + DRF + JWT）

## 后端配置

1. 安装依赖：在仓库根目录使用 `uv sync`（或自行安装 Django/DRF 等与 `backend` 一致的环境）。
2. 配置环境变量（参考 `backend/.env.example`）：
   - `BACKEND_ALLOWED_HOSTS=api.example.com`
   - `BACKEND_CORS_ALLOWED_ORIGINS=https://app.example.com`
3. 迁移并启动（在 `backend/` 目录）：
   - `python manage.py migrate`
   - `gunicorn config.wsgi:application -b 127.0.0.1:8000`

## 前端配置

1. 进入前端目录：
   - `cd frontend`
2. 安装依赖：
   - `npm install`
3. 构建：
   - `npm run build`
4. 部署 `dist/` 到 `app.example.com` 的 Nginx root。

## Nginx 示例

```nginx
server {
    listen 80;
    server_name app.example.com;
    root /var/www/xinhuo-app/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}

server {
    listen 80;
    server_name api.example.com;

    location /static/ {
        alias /srv/xinhuo/backend/staticfiles/;
    }

    location /media/ {
        alias /srv/xinhuo/backend/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 首次联调检查

1. `POST https://api.example.com/api/auth/token/` 可返回 access/refresh。
2. `GET https://api.example.com/api/auth/me/` 携带 Bearer token 可返回用户信息。
3. 前端登录后能访问：
   - `/data-screen`
   - `/hall`
   - `/products`
   - `/payment-stats`
4. 收款统计筛选后导出 CSV，内容与筛选条件一致。
