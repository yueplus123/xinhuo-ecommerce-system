"""写入 UI 预览用 SKU 价格假数据（覆盖 fghdg 平台 3 个 SKU，展示四种价格类型）。"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from backend.apps.catalog.models import Platform, SKU, SKUPriceItem

SKU_PRICE_PREVIEW = {
    "dsfs": {
        "price_type": SKU.PRICE_TYPE_USD_SINGLE,
        "price_notice": "单一美金档位，适用于固定面额代充。",
        "items": [
            ("$5", "36.50", "付款后 15 分钟内处理"),
        ],
    },
    "vfdb": {
        "price_type": SKU.PRICE_TYPE_USD_TIER,
        "price_notice": "美金价格随汇率浮动，下单前请与客户确认档位。",
        "items": [
            ("$5", "36.00", "需美区 PayPal 账号"),
            ("$10", "70.00", ""),
            ("$20", "135.00", "大额充值需提前 30 分钟预约"),
        ],
    },
    "42542": {
        "price_type": SKU.PRICE_TYPE_PACKAGE,
        "price_notice": "套餐价格每周一更新，请以当日报价为准。",
        "items": [
            ("月卡", "88.00", "仅限新用户首购"),
            ("季卡", "238.00", ""),
            ("年卡", "688.00", "含专属客服通道"),
        ],
    },
    "vbx": {
        "price_type": SKU.PRICE_TYPE_JPY_RECHARGE,
        "price_notice": "日元面额为平台标准档位，非自定义金额。",
        "items": [
            ("1000円", "52.00", ""),
            ("3000円", "148.00", "热门档位，库存紧张时请提前确认"),
            ("5000円", "245.00", ""),
        ],
    },
}


def main():
    platform = Platform.objects.filter(name="fghdg").first()
    platform_xcd = Platform.objects.filter(name="xcd").first()
    targets = []
    if platform:
        targets.append(platform)
    if platform_xcd:
        targets.append(platform_xcd)
    if not targets:
        print("未找到演示平台，跳过。")
        return

    updated = 0
    for pf in targets:
        for sku in SKU.objects.filter(business__platform=pf):
            cfg = SKU_PRICE_PREVIEW.get(sku.name)
            if not cfg:
                continue
            sku.price_type = cfg["price_type"]
            sku.price_notice = cfg["price_notice"]
            sku.save(update_fields=["price_type", "price_notice"])
            sku.price_items.all().delete()
            for order, (label, rmb, notice) in enumerate(cfg["items"], start=1):
                SKUPriceItem.objects.create(
                    sku=sku,
                    label=label,
                    rmb_amount=rmb,
                    notice=notice,
                    sort_order=order * 10,
                )
            updated += 1
            print(f"  SKU {sku.name}: {cfg['price_type']} × {len(cfg['items'])} 档")

    print(f"完成：更新 {updated} 个 SKU 价格演示数据。")


if __name__ == "__main__":
    main()
