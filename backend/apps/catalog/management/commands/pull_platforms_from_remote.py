"""从线上（同源 DRF）拉取「平台」列表（名称、网址等），写入本地 JSON/CSV，供 import_platforms 导入。"""

import csv
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


def _http_json(method: str, url: str, *, headers: dict | None = None, payload: dict | None = None, timeout: int = 90):
    data_bytes = None
    hdrs = dict(headers or {})
    if payload is not None:
        data_bytes = json.dumps(payload).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data_bytes, headers=hdrs, method=method)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise CommandError(f"HTTP {e.code} {url}\n{body}") from e
    except urllib.error.URLError as e:
        raise CommandError(f"请求失败：{url}\n{e}") from e
    if not raw.strip():
        return None
    return json.loads(raw)


def _normalize_api_root(api_root: str) -> str:
    s = (api_root or "").strip().rstrip("/")
    if not s:
        raise CommandError("请提供非空的 --api-root，例如 https://你的域名/api")
    return s


def _collect_platform_rows(data) -> list[dict]:
    """兼容无分页列表、DRF 分页 {results,next}、以及直接为 list。"""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        if "results" in data and isinstance(data["results"], list):
            return [x for x in data["results"] if isinstance(x, dict)]
    return []


def _next_url(data) -> str | None:
    if not isinstance(data, dict):
        return None
    n = data.get("next")
    if not n:
        return None
    if isinstance(n, str) and n.strip():
        return n.strip()
    return None


class Command(BaseCommand):
    help = (
        "使用职员账号 JWT 调用线上 GET /platforms/，导出名称与网址等字段到本地文件；"
        "随后在本机执行 import_platforms 写入新项目。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--api-root",
            required=True,
            help="线上 API 根路径，如 https://example.com/api（不要尾斜杠也可）",
        )
        g = parser.add_mutually_exclusive_group(required=True)
        g.add_argument("--username", help="与 --password 一起用于 POST /auth/token/")
        parser.add_argument("--password", default="", help="职员账号密码")
        g.add_argument("--access-token", dest="access_token", help="已有 JWT access，跳过登录")
        parser.add_argument(
            "-o",
            "--output",
            default="",
            help="输出文件路径；默认：当前目录 platforms_remote.json",
        )
        parser.add_argument(
            "--format",
            choices=("json", "csv"),
            default="json",
            help="输出格式（默认 json；csv 带 UTF-8 BOM 便于 Excel）",
        )

    def handle(self, *args, **options):
        api_root = _normalize_api_root(options["api_root"])
        token = (options.get("access_token") or "").strip()
        user = (options.get("username") or "").strip()
        password = options.get("password") or ""

        if not token:
            if not user:
                raise CommandError("请提供 --username/--password 或 --access-token")
            if not password:
                raise CommandError("使用 --username 时请同时提供 --password")
            tok_url = f"{api_root}/auth/token/"
            tok = _http_json("POST", tok_url, payload={"username": user, "password": password})
            token = (tok or {}).get("access") or ""
            if not token:
                raise CommandError("登录失败：响应中无 access token")

        headers = {"Authorization": f"Bearer {token}"}
        url = f"{api_root}/platforms/"
        rows_out: list[dict] = []
        seen = 0
        while url:
            data = _http_json("GET", url, headers=headers)
            chunk = _collect_platform_rows(data)
            for p in chunk:
                rows_out.append(
                    {
                        "name": (p.get("name") or "").strip(),
                        "url": (p.get("url") or "").strip(),
                        "status": (p.get("status") or "").strip() or "on_sale",
                        "note": (p.get("note") or "").strip(),
                        "sort_order": int(p.get("sort_order") or 0),
                    }
                )
                seen += 1
            nxt = _next_url(data)
            if nxt and nxt == url:
                break
            url = nxt or ""

        by_name: dict[str, dict] = {}
        for r in rows_out:
            if r["name"]:
                by_name[r["name"]] = r
        rows_out = list(by_name.values())

        raw_out = (options.get("output") or "").strip()
        base = Path(raw_out).expanduser() if raw_out else Path.cwd() / "platforms_remote"
        out_path = base.with_suffix(".csv" if options["format"] == "csv" else ".json")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        if options["format"] == "csv":
            with out_path.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["name", "url", "status", "note", "sort_order"])
                w.writeheader()
                for r in rows_out:
                    w.writerow(r)
        else:
            out_path.write_text(json.dumps(rows_out, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(
            self.style.SUCCESS(f"已从线上拉取平台 {len(rows_out)} 条（原始条目 {seen}），已写入：{out_path.resolve()}")
        )
