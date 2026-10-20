"""员工商品库：一次返回 平台 → 业务 → SKU 的完整目录（只读）。

给 /library.html（淘宝样式的员工商品库页面）使用，结构与 scripts/export_catalog.py 的导出一致。
不包含账号密码、卡号、收款记录等敏感数据。
"""
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.catalog.models import SKU, Business, Platform, TutorialPool, UsdProxyPriceTier

from .views import StaffOnlyPermission

TUTORIAL_SEP = " / "  # 与 manage_sku._TUTORIAL_SEP 一致


def _num(v):
    if v is None:
        return None
    f = float(v)
    return int(f) if f.is_integer() else f


def _file_url(f):
    try:
        return f.url if f else ""
    except ValueError:
        return ""


def build_catalog_library():
    price_type_labels = dict(SKU.PRICE_TYPE_CHOICES)
    tutorials = {t.name: t.detail_url for t in TutorialPool.objects.all()}
    platforms = Platform.objects.prefetch_related(
        "platform_tags",
        Prefetch(
            "businesses",
            queryset=Business.objects.order_by("id").prefetch_related(
                Prefetch(
                    "skus",
                    queryset=SKU.objects.order_by("id").prefetch_related(
                        "price_items", "quick_phrases", "channel_tags", "member_images"
                    ),
                )
            ),
        ),
    ).order_by("sort_order", "id")

    out = []
    for p in platforms:
        businesses = []
        for b in p.businesses.all():
            skus = []
            for s in b.skus.all():
                names = [n.strip() for n in (s.tutorial_text or "").split(TUTORIAL_SEP) if n.strip()]
                imgs = [_file_url(s.image)] + [_file_url(i.image) for i in s.member_images.all()]
                imgs = list(dict.fromkeys(u for u in imgs if u))  # 主截图与会员截图常是同一个文件
                skus.append({
                    "id": s.id,
                    "name": s.name,
                    "status": s.status,
                    "price": _num(s.price),
                    "price_type": s.price_type or "",
                    "price_type_label": price_type_labels.get(s.price_type, ""),
                    "price_notice": s.price_notice or "",
                    "precaution": s.precaution or "",
                    "note": s.note or "",
                    "extend_config": s.extend_config or "",
                    "price_items": [
                        {"label": i.label, "rmb_amount": _num(i.rmb_amount), "notice": i.notice}
                        for i in s.price_items.all()
                    ],
                    "phrases": [x.content for x in s.quick_phrases.all()],
                    "tutorials": [{"name": n, "url": tutorials.get(n, "")} for n in names],
                    "channels": [t.name for t in s.channel_tags.all()],
                    "image_urls": imgs,
                    "images": len(imgs),
                })
            businesses.append({"id": b.id, "name": b.name, "status": b.status, "skus": skus})
        out.append({
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "note": p.note or "",
            "url": p.url or "",
            "tags": [t.name for t in p.platform_tags.all()],
            "businesses": businesses,
        })

    return {
        "exported_at": timezone.localtime().strftime("%Y-%m-%d %H:%M"),
        "site": "",  # 同源访问，截图用相对地址
        "price_types": price_type_labels,
        "usd_proxy_tiers": [
            {"usd_range": t.usd_range, "rate_percent": _num(t.rate_percent)}
            for t in UsdProxyPriceTier.objects.order_by("sort_order", "id")
        ],
        "platforms": out,
    }


class CatalogLibraryAPIView(APIView):
    permission_classes = [StaffOnlyPermission]
    guest_allowed = True  # 与「平台/商品」页一致，游客也可查看

    def get(self, request):
        return Response(build_catalog_library())
