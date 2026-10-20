#!/usr/bin/env python3
"""只读导出：平台 / 业务 / SKU 及其价格档位、注意事项、话术、教程，输出 JSON。

不修改任何数据（数据库以只读模式打开）。不导出账号密码、卡号、收款等敏感表。

用法（服务器上）：
    python3 scripts/export_catalog.py > /root/xh_catalog.json
    python3 scripts/export_catalog.py --db /路径/backend.sqlite3 > out.json
"""
import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "backend" / "data" / "backend.sqlite3"
TUTORIAL_SEP = " / "  # 与 backend/apps/api/manage_sku.py 的 _TUTORIAL_SEP 一致


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    q = lambda sql: [dict(r) for r in con.execute(sql).fetchall()]

    def cols(table):
        return {r["name"] for r in con.execute(f"pragma table_info({table})")}

    tutorials = {t["name"]: t for t in q("select name, detail_url from catalog_tutorialpool")}
    prices = defaultdict(list)
    for r in q("select sku_id, label, rmb_amount, notice from catalog_skupriceitem order by sort_order, id"):
        prices[r.pop("sku_id")].append(r)
    phrases = defaultdict(list)
    for r in q("select sku_id, content from catalog_quickphrase order by \"order\", id"):
        phrases[r["sku_id"]].append(r["content"])
    images = defaultdict(int)
    for r in q("select sku_id, count(*) n from catalog_skuimage group by sku_id"):
        images[r["sku_id"]] = r["n"]

    sku_cols = cols("catalog_sku")
    want = ["id", "name", "status", "price", "price_type", "price_notice", "precaution", "note",
            "image", "tutorial_text", "business_id"]
    sel = ", ".join(c for c in want if c in sku_cols)
    skus_by_biz = defaultdict(list)
    for s in q(f"select {sel} from catalog_sku order by business_id, id"):
        names = [n.strip() for n in (s.get("tutorial_text") or "").split(TUTORIAL_SEP) if n.strip()]
        skus_by_biz[s["business_id"]].append({
            "id": s["id"],
            "name": s["name"],
            "status": s.get("status"),
            "price": s.get("price"),
            "price_type": s.get("price_type"),
            "price_notice": s.get("price_notice") or "",
            "precaution": s.get("precaution") or "",
            "note": s.get("note") or "",
            "price_items": prices.get(s["id"], []),
            "phrases": phrases.get(s["id"], []),
            "tutorials": [{"name": n, "url": (tutorials.get(n) or {}).get("detail_url", "")} for n in names],
            "images": images.get(s["id"], 0) + (1 if s.get("image") else 0),
        })

    biz_by_plat = defaultdict(list)
    for b in q("select id, name, status, platform_id from catalog_business order by platform_id, id"):
        biz_by_plat[b["platform_id"]].append({
            "id": b["id"], "name": b["name"], "status": b["status"], "skus": skus_by_biz.get(b["id"], []),
        })

    out = []
    for p in q("select id, name, status, note, sort_order from catalog_platform order by sort_order, id"):
        out.append({"id": p["id"], "name": p["name"], "status": p["status"], "note": p["note"] or "",
                    "businesses": biz_by_plat.get(p["id"], [])})

    json.dump(out, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    n_b = sum(len(p["businesses"]) for p in out)
    n_s = sum(len(b["skus"]) for p in out for b in p["businesses"])
    print(f"\n已导出：平台 {len(out)}，业务 {n_b}，SKU {n_s}（只读，未修改数据）", file=sys.stderr)


if __name__ == "__main__":
    main()
