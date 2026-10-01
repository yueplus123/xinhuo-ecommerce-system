# 薪火前端（vue-element-plus-admin 完整版）

旧前端备份目录：`../frontend-backup-pre-element-admin`

## 本地运行

```powershell
# 后端（另开终端）
cd D:\桌面\xinhuoxitong\django-jazzmin-main
$env:PYTHONPATH="D:\桌面\xinhuoxitong\django-jazzmin-main"
.\.venv\Scripts\python.exe backend\manage.py runserver 8001

# 前端
cd D:\桌面\xinhuoxitong\django-jazzmin-main\frontend
pnpm install
pnpm run dev
```

打开 http://localhost:5173/

- Vite 代理 `/api`、`/media` → `http://127.0.0.1:8001`
- 登录走 Django JWT（`/api/auth/token/`），不改后端数据
- 业务页在 `src/views/Xinhuo/`
- 记账 React 子应用在 `src/ledger-app/`
