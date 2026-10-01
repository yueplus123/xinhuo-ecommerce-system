"""微信机器人 → 薪火平台商品查询（仅返回平台名 + 商品名，不含价格等）。"""

from __future__ import annotations

from django.conf import settings
from django.db.models import Q

from backend.apps.catalog.models import Platform, SKU


def api_key_ok(request) -> bool:
    expected = (getattr(settings, "EXTERNAL_PUSH_API_KEY", "") or "").strip()
    if not expected:
        return False
    got = (
        (request.headers.get("X-Api-Key") or "")
        or (request.META.get("HTTP_X_API_KEY") or "")
        or ""
    ).strip()
    if not got:
        auth = (request.headers.get("Authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            got = auth[7:].strip()
    return bool(got) and got == expected


def query_bot_products(
    *,
    q: str = "",
    platform: str = "",
    limit: int = 50,
    on_sale_only: bool = True,
) -> dict:
    """
    供 BOT 查商品：每条仅 platform_name + product_name（SKU 名）。
    """
    q = (q or "").strip()
    platform = (platform or "").strip()
    try:
        limit = min(200, max(1, int(limit or 50)))
    except (TypeError, ValueError):
        limit = 50

    qs = SKU.objects.select_related("business__platform")
    if on_sale_only:
        qs = qs.filter(
            status=SKU.STATUS_ON_SALE,
            business__status=Platform.STATUS_ON_SALE,
            business__platform__status=Platform.STATUS_ON_SALE,
        )
    if platform:
        qs = qs.filter(business__platform__name__icontains=platform)
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(business__name__icontains=q)
            | Q(business__platform__name__icontains=q)
        )

    qs = qs.order_by(
        "business__platform__sort_order",
        "business__platform__id",
        "business__id",
        "id",
    )

    results = []
    for sku in qs[:limit]:
        plat = getattr(getattr(sku, "business", None), "platform", None)
        platform_name = (getattr(plat, "name", None) or "").strip()
        product_name = (sku.name or "").strip()
        if not platform_name or not product_name:
            continue
        results.append(
            {
                "platform_name": platform_name,
                "product_name": product_name,
            }
        )

    return {
        "ok": True,
        "count": len(results),
        "q": q,
        "platform": platform,
        "results": results,
    }


def format_bot_product_reply(payload: dict) -> str:
    """把查询结果格式化成群聊可读文本（仍不含价格）。"""
    rows = payload.get("results") or []
    q = (payload.get("q") or "").strip()
    if not rows:
        tip = f"「{q}」" if q else ""
        return f"未找到相关商品{tip}。可发：查商品 或 查商品 关键词"

    lines = [f"商品目录（共 {len(rows)} 条）", "--------------"]
    for r in rows:
        lines.append(f"{r.get('platform_name', '')} · {r.get('product_name', '')}")
    lines.append("--------------")
    if q:
        lines.append(f"关键词：{q}")
    return "\n".join(lines)


DEMO_PREFIX = "BOT演示-"


def seed_bot_product_demo(*, replace: bool = True) -> dict:
    """写入 BOT 查商品测试用平台/业务/SKU（仅名称，便于联调）。"""
    from backend.apps.catalog.models import Business

    if replace:
        Platform.objects.filter(name__startswith=DEMO_PREFIX).delete()

    samples = [
        ("Patreon", ["会员月卡", "会员年卡", "创作者赞助档"]),
        ("Fanbox", ["基础计划", "高级计划", "限定画集"]),
        ("Booth", ["数字商品A", "数字商品B"]),
        ("Pixiv", ["充币档位小", "充币档位大"]),
    ]
    created_platforms = 0
    created_skus = 0
    for i, (plat_name, sku_names) in enumerate(samples):
        plat = Platform.objects.create(
            name=f"{DEMO_PREFIX}{plat_name}",
            status=Platform.STATUS_ON_SALE,
            sort_order=1000 + i,
            note="bot-product-demo",
            url="",
        )
        created_platforms += 1
        biz = Business.objects.create(
            platform=plat,
            name="默认业务",
            status=Business.STATUS_ON_SALE,
        )
        for name in sku_names:
            SKU.objects.create(
                business=biz,
                name=name,
                status=SKU.STATUS_ON_SALE,
            )
            created_skus += 1

    return {
        "ok": True,
        "platforms": created_platforms,
        "skus": created_skus,
        "prefix": DEMO_PREFIX,
    }
