#!/usr/bin/env python3
"""只读导出：平台 / 业务 / SKU 及其价格档位、注意事项、话术、教程、标签、截图地址，输出 JSON。

不修改任何数据（数据库以只读模式打开）。不导出账号密码、卡号、收款等敏感表。
截图只导出文件地址（/media/...），不导出图片本身。

用法（服务器上）：
    python3 scripts/export_catalog.py > /root/xh_catalog.json
    python3 scripts/export_catalog.py --site https://你的域名 > out.json   # 指定截图所在站点
"""
import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "backend" / "data" / "backend.sqlite3"
TUTORIAL_SEP = " / "  # 与 backend/apps/api/manage_sku.py 的 _TUTORIAL_SEP 一致
MEDIA_URL = "/media/"
PRICE_TYPES = {
    "cny_single": "单一人民币",
    "usd_single": "美金（单一）",
    "usd_tier": "美金（多档）",
    "package": "套餐",
    "jpy_recharge": "日元充值",
    "usd_proxy": "按美金代付收费",
}


def detect_site():
    """从 .env 里只读取站点地址相关的几项，用来拼截图的完整地址。"""
    env = {}
    for p in (ROOT / ".env", ROOT / "backend" / ".env"):
        if p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    if k.strip() in ("STAFF_FRONTEND_BASE_URL", "BACKEND_CORS_ALLOWED_ORIGINS", "BACKEND_ALLOWED_HOSTS"):
                        env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    if env.get("STAFF_FRONTEND_BASE_URL"):
        return env["STAFF_FRONTEND_BASE_URL"].rstrip("/")
    for o in env.get("BACKEND_CORS_ALLOWED_ORIGINS", "").split(","):
        o = o.strip()
        if o.startswith("http") and "localhost" not in o and "127.0.0.1" not in o:
            return o.rstrip("/")
    for h in env.get("BACKEND_ALLOWED_HOSTS", "").split(","):
        h = h.strip()
        if h and h not in ("localhost", "127.0.0.1", "testserver", "*") and not h.startswith("."):
            return "https://" + h
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--site", default="", help="截图所在站点，如 https://example.com；不填则从 .env 推断")
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    q = lambda sql, *a: [dict(r) for r in con.execute(sql, a).fetchall()]
    tables = {r["name"] for r in q("select name from sqlite_master where type='table'")}

    def cols(table):
        return {r["name"] for r in con.execute(f"pragma table_info({table})")}

    def media(path):
        return (MEDIA_URL + path) if path else ""

    # 标签（平台标签 / 渠道标签）
    tag_name = {t["id"]: t["name"] for t in q("select id, name from catalog_tag order by \"order\", id")} if "catalog_tag" in tables else {}

    def m2m(table, owner_col):
        out = defaultdict(list)
        if table in tables:
            for r in q(f"select {owner_col} o, tag_id t from {table} order by id"):
                if r["t"] in tag_name:
                    out[r["o"]].append(tag_name[r["t"]])
        return out

    plat_tags = m2m("catalog_platform_platform_tags", "platform_id")
    sku_channels = m2m("catalog_sku_channel_tags", "sku_id")

    tutorials = {t["name"]: t for t in q("select name, detail_url from catalog_tutorialpool")}
    prices = defaultdict(list)
    for r in q("select sku_id, label, rmb_amount, notice from catalog_skupriceitem order by sort_order, id"):
        prices[r.pop("sku_id")].append(r)
    phrases = defaultdict(list)
    for r in q("select sku_id, content from catalog_quickphrase order by \"order\", id"):
        phrases[r["sku_id"]].append(r["content"])
    images = defaultdict(list)
    for r in q("select sku_id, image from catalog_skuimage order by sort_order, id"):
        if r["image"]:
            images[r["sku_id"]].append(media(r["image"]))

    sku_cols = cols("catalog_sku")
    want = ["id", "name", "status", "price", "price_type", "price_notice", "precaution", "note",
            "image", "tutorial_text", "extend_config", "business_id"]
    sel = ", ".join(c for c in want if c in sku_cols)
    skus_by_biz = defaultdict(list)
    for s in q(f"select {sel} from catalog_sku order by business_id, id"):
        names = [n.strip() for n in (s.get("tutorial_text") or "").split(TUTORIAL_SEP) if n.strip()]
        # 主截图和会员截图常是同一个文件，去重
        imgs = list(dict.fromkeys(([media(s["image"])] if s.get("image") else []) + images.get(s["id"], [])))
        pt = s.get("price_type") or ""
        skus_by_biz[s["business_id"]].append({
            "id": s["id"],
            "name": s["name"],
            "status": s.get("status"),
            "price": s.get("price"),
            "price_type": pt,
            "price_type_label": PRICE_TYPES.get(pt, ""),
            "price_notice": s.get("price_notice") or "",
            "precaution": s.get("precaution") or "",
            "note": s.get("note") or "",
            "extend_config": s.get("extend_config") or "",
            "price_items": prices.get(s["id"], []),
            "phrases": phrases.get(s["id"], []),
            "tutorials": [{"name": n, "url": (tutorials.get(n) or {}).get("detail_url", "")} for n in names],
            "channels": sku_channels.get(s["id"], []),
            "image_urls": imgs,
            "images": len(imgs),
        })

    biz_by_plat = defaultdict(list)
    for b in q("select id, name, status, platform_id from catalog_business order by platform_id, id"):
        biz_by_plat[b["platform_id"]].append({
            "id": b["id"], "name": b["name"], "status": b["status"], "skus": skus_by_biz.get(b["id"], []),
        })

    plat_cols = cols("catalog_platform")
    psel = ", ".join(c for c in ["id", "name", "status", "note", "url", "sort_order"] if c in plat_cols)
    platforms = []
    for p in q(f"select {psel} from catalog_platform order by sort_order, id"):
        platforms.append({"id": p["id"], "name": p["name"], "status": p["status"], "note": p.get("note") or "",
                          "url": p.get("url") or "", "tags": plat_tags.get(p["id"], []),
                          "businesses": biz_by_plat.get(p["id"], [])})

    usd_tiers = []
    if "catalog_usdproxypricetier" in tables:
        usd_tiers = q("select usd_range, rate_percent from catalog_usdproxypricetier order by sort_order, id")

    out = {
        "exported_at": date.today().isoformat(),
        "site": (args.site or detect_site()).rstrip("/"),
        "price_types": PRICE_TYPES,
        "usd_proxy_tiers": usd_tiers,
        "platforms": platforms,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    n_b = sum(len(p["businesses"]) for p in platforms)
    skus = [s for p in platforms for b in p["businesses"] for s in b["skus"]]
    print(f"\n已导出：平台 {len(platforms)}，业务 {n_b}，SKU {len(skus)}；"
          f"渠道标签 {sum(1 for s in skus if s['channels'])} 个 SKU 有，"
          f"截图 {sum(s['images'] for s in skus)} 张，美金代付价格档 {len(usd_tiers)} 条；"
          f"截图站点：{out['site'] or '未识别，请加 --site'}（只读，未修改数据）", file=sys.stderr)


if __name__ == "__main__":
    main()
