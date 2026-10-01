"""
本地职员端预览：写入充实的演示平台 / 业务 / SKU 数据。

用法（项目根或 backend 目录均可）:
  python backend/scripts/seed_local_preview.py
  python backend/scripts/seed_local_preview.py --purge   # 先删「演示·」平台再重建

会创建/更新:
  - 6 个「演示·」开头平台（单业务 / 多业务 / 各状态）
  - 每类价格类型、教程、快捷语、渠道标签、注意事项
  - 顺带补全已有 xcd / fghdg 平台 SKU 的渠道与教程
"""

from __future__ import annotations

import argparse
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from decimal import Decimal

from backend.apps.catalog.models import (
    Business,
    PaymentTutorial,
    Platform,
    QuickPhrase,
    SKU,
    SKUPriceItem,
    Tag,
    TutorialPool,
)

DEMO_PREFIX = "演示·"

TUTORIAL_CATALOG = [
    ("PayPal 跨境支付流程", "https://example.com/tutorial/paypal-flow"),
    ("Fanbox 订阅开通指南", "https://example.com/tutorial/fanbox-guide"),
    ("信用卡 3DS 验证说明", "https://example.com/tutorial/3ds-verify"),
    ("代充失败排错步骤", "https://example.com/tutorial/troubleshoot"),
    ("退款与售后处理规范", "https://example.com/tutorial/refund-policy"),
    ("新用户首单操作教程", "https://example.com/tutorial/first-order"),
    ("海外账号绑定注意事项", "https://example.com/tutorial/account-bind"),
]

CHANNEL_TAG_NAMES = [
    "汇通5329",
    "91卡券",
    "supay 汇通卡",
    "淘宝",
    "企业微信",
    "Discord",
]

PHRASE_POOL = [
    "您好，订单已收到，正在为您处理中，请稍候。",
    "支付成功后请截图回传，方便核验到账。",
    "教程已发送，请按步骤操作。",
    "请勿重复下单，避免重复扣费。",
    "当前高峰期预计 15-30 分钟处理完成。",
    "若支付失败，请更换浏览器或无痕模式重试。",
    "如出现风控提示，请截图联系客服。",
    "发货完成后会推送通知，请注意查收。",
]

# 演示平台结构：name, status, sort_order, platform_tag_names, businesses[]
DEMO_PLATFORMS = [
    {
        "name": f"{DEMO_PREFIX}Fanza",
        "status": Platform.STATUS_ON_SALE,
        "sort_order": 10,
        "platform_tags": ["fanbox"],
        "note": "单业务平台演示：点卡片直接进入 SKU",
        "businesses": [
            {
                "name": "标准订阅",
                "skus": [
                    {
                        "name": "月会员",
                        "status": SKU.STATUS_ON_SALE,
                        "price_type": SKU.PRICE_TYPE_USD_SINGLE,
                        "price_notice": "单一美金档位，适用于固定订阅面额。",
                        "price_items": [("$9.99", "72.00", "美区账号优先")],
                        "tutorial_idx": [0, 1],
                        "phrase_idx": [0, 1, 2],
                        "channels": ["汇通5329", "91卡券"],
                        "note": "单业务 + 美金单一价 + 教程快捷语齐全",
                    },
                    {
                        "name": "年会员",
                        "status": SKU.STATUS_ON_SALE,
                        "price_type": SKU.PRICE_TYPE_CNY_SINGLE,
                        "price_notice": "",
                        "price_items": [("", "688.00", "")],
                        "tutorial_idx": [1],
                        "phrase_idx": [0],
                        "channels": ["淘宝"],
                        "note": "旧式单一人民币（无左侧标签）",
                    },
                ],
            }
        ],
    },
    {
        "name": f"{DEMO_PREFIX}Fanbox",
        "status": Platform.STATUS_ON_SALE,
        "sort_order": 20,
        "platform_tags": ["fanbox", "pixiv"],
        "note": "多业务手风琴演示",
        "businesses": [
            {
                "name": "画师A 专区",
                "skus": [
                    {
                        "name": "月赞助",
                        "status": SKU.STATUS_ON_SALE,
                        "price_type": SKU.PRICE_TYPE_PACKAGE,
                        "price_notice": "套餐价格每周一更新。",
                        "price_items": [
                            ("月卡", "88.00", "仅限新用户"),
                            ("季卡", "238.00", ""),
                            ("年卡", "688.00", "含专属客服"),
                        ],
                        "tutorial_idx": [0, 1, 2, 3],
                        "phrase_idx": [0, 1, 2, 3, 4],
                        "channels": ["汇通5329", "企业微信"],
                        "note": "套餐价 + 多教程 + 多快捷语",
                    },
                    {
                        "name": "单次支援",
                        "status": SKU.STATUS_PENDING_TEST,
                        "price_type": SKU.PRICE_TYPE_USD_TIER,
                        "price_notice": "美金多档，汇率浮动。",
                        "price_items": [
                            ("$3", "22.00", ""),
                            ("$5", "36.00", "需美区 PayPal"),
                            ("$10", "70.00", ""),
                        ],
                        "tutorial_idx": [2],
                        "phrase_idx": [5],
                        "channels": ["91卡券"],
                        "note": "待测试状态演示",
                    },
                ],
            },
            {
                "name": "画师B 专区",
                "skus": [
                    {
                        "name": "高级档",
                        "status": SKU.STATUS_ON_SALE,
                        "price_type": SKU.PRICE_TYPE_JPY_RECHARGE,
                        "price_notice": "日元标准面额，非自定义金额。",
                        "price_items": [
                            ("1000円", "52.00", ""),
                            ("3000円", "148.00", "热门档位"),
                            ("5000円", "245.00", ""),
                        ],
                        "tutorial_idx": [4, 5],
                        "phrase_idx": [6, 7],
                        "channels": ["supay 汇通卡", "Discord"],
                        "note": "日元充值档演示",
                    },
                    {
                        "name": "体验档",
                        "status": SKU.STATUS_ON_SALE,
                        "price_type": "",
                        "price_notice": "",
                        "price_items": [],
                        "tutorial_idx": [],
                        "phrase_idx": [],
                        "channels": [],
                        "note": "暂无价格 / 暂无教程（空状态演示）",
                    },
                ],
            },
            {
                "name": "合集打包",
                "skus": [
                    {
                        "name": "三合一礼包",
                        "status": SKU.STATUS_ON_SALE,
                        "price_type": SKU.PRICE_TYPE_PACKAGE,
                        "price_notice": "打包价含三个画师内容。",
                        "price_items": [("豪华礼包", "199.00", "限时优惠")],
                        "tutorial_idx": [0, 6],
                        "phrase_idx": [0, 2],
                        "channels": ["汇通5329"],
                        "note": "",
                    },
                ],
            },
        ],
    },
    {
        "name": f"{DEMO_PREFIX}Patreon",
        "status": Platform.STATUS_ON_SALE,
        "sort_order": 30,
        "platform_tags": ["patreon"],
        "note": "",
        "businesses": [
            {
                "name": "创作者订阅",
                "skus": [
                    {
                        "name": "Tier 1",
                        "status": SKU.STATUS_ON_SALE,
                        "price_type": SKU.PRICE_TYPE_USD_TIER,
                        "price_notice": "Creator 档位以 Patreon 页面为准。",
                        "price_items": [
                            ("$5", "36.00", ""),
                            ("$10", "70.00", ""),
                            ("$25", "175.00", "含独家内容"),
                        ],
                        "tutorial_idx": [0, 3],
                        "phrase_idx": [0, 1],
                        "channels": ["汇通5329", "91卡券"],
                        "note": "",
                    },
                    {
                        "name": "Tier 2",
                        "status": SKU.STATUS_OFF_SALE,
                        "price_type": SKU.PRICE_TYPE_USD_SINGLE,
                        "price_notice": "",
                        "price_items": [("$15", "105.00", "暂时禁售")],
                        "tutorial_idx": [5],
                        "phrase_idx": [],
                        "channels": ["淘宝"],
                        "note": "禁售状态演示",
                    },
                ],
            }
        ],
    },
    {
        "name": f"{DEMO_PREFIX}Pixiv",
        "status": Platform.STATUS_ON_SALE,
        "sort_order": 40,
        "platform_tags": ["pixiv"],
        "note": "双业务中等规模",
        "businesses": [
            {
                "name": "Fanbox 代充",
                "skus": [
                    {
                        "name": "500円档",
                        "status": SKU.STATUS_ON_SALE,
                        "price_type": SKU.PRICE_TYPE_JPY_RECHARGE,
                        "price_notice": "",
                        "price_items": [("500円", "28.00", ""), ("1000円", "52.00", "")],
                        "tutorial_idx": [1],
                        "phrase_idx": [2],
                        "channels": ["91卡券"],
                        "note": "",
                    },
                ],
            },
            {
                "name": "Premium 会员",
                "skus": [
                    {
                        "name": "月费",
                        "status": SKU.STATUS_ON_SALE,
                        "price_type": SKU.PRICE_TYPE_CNY_SINGLE,
                        "price_notice": "人民币固定报价。",
                        "price_items": [("", "45.00", "")],
                        "tutorial_idx": [1, 2],
                        "phrase_idx": [0],
                        "channels": ["企业微信"],
                        "note": "",
                    },
                    {
                        "name": "年费",
                        "status": SKU.STATUS_ON_SALE,
                        "price_type": SKU.PRICE_TYPE_PACKAGE,
                        "price_notice": "",
                        "price_items": [("年费套餐", "480.00", "比月付省 15%")],
                        "tutorial_idx": [],
                        "phrase_idx": [1],
                        "channels": ["淘宝", "汇通5329"],
                        "note": "无教程、有快捷语",
                    },
                ],
            },
        ],
    },
    {
        "name": f"{DEMO_PREFIX}待测试平台",
        "status": Platform.STATUS_PENDING_TEST,
        "sort_order": 50,
        "platform_tags": [],
        "note": "平台级「待测试」状态",
        "businesses": [
            {
                "name": "内测业务",
                "skus": [
                    {
                        "name": "内测 SKU",
                        "status": SKU.STATUS_PENDING_TEST,
                        "price_type": SKU.PRICE_TYPE_USD_SINGLE,
                        "price_notice": "内测价，勿对外报价。",
                        "price_items": [("$1", "7.50", "")],
                        "tutorial_idx": [6],
                        "phrase_idx": [7],
                        "channels": ["Discord"],
                        "note": "",
                    },
                ],
            }
        ],
    },
    {
        "name": f"{DEMO_PREFIX}已下架",
        "status": Platform.STATUS_OFF_SALE,
        "sort_order": 60,
        "platform_tags": [],
        "note": "平台级「禁售」状态",
        "businesses": [
            {
                "name": "历史业务",
                "skus": [
                    {
                        "name": "旧 SKU",
                        "status": SKU.STATUS_OFF_SALE,
                        "price_type": SKU.PRICE_TYPE_CNY_SINGLE,
                        "price_notice": "",
                        "price_items": [("", "99.00", "")],
                        "tutorial_idx": [],
                        "phrase_idx": [],
                        "channels": [],
                        "note": "已下架商品",
                    },
                ],
            }
        ],
    },
]

# 补全已有本地平台 SKU
LEGACY_SKU_ENRICH = {
    "xcd": {
        "2222": {
            "price_type": SKU.PRICE_TYPE_CNY_SINGLE,
            "price_notice": "旧 price 字段迁移的单一人民币。",
            "price_items": [("", "244.00", "")],
            "tutorial_idx": [0, 2],
            "phrase_idx": [0, 3],
            "channels": ["汇通5329"],
            "note": "xcd 平台第二 SKU，补教程与渠道",
        },
    },
    "fghdg": {
        "vfdb": {
            "price_type": SKU.PRICE_TYPE_USD_TIER,
            "price_notice": "美金价格随汇率浮动，下单前请与客户确认档位。",
            "price_items": [
                ("$5", "36.00", "需美区 PayPal 账号"),
                ("$10", "70.00", ""),
                ("$20", "135.00", "大额充值需提前 30 分钟预约"),
            ],
            "tutorial_idx": [0, 1, 2],
            "phrase_idx": [0, 1, 2],
            "channels": ["汇通5329", "91卡券"],
            "note": "演示备注：美金多档 + 教程 + 快捷语",
        },
        "42542": {
            "price_type": SKU.PRICE_TYPE_PACKAGE,
            "price_notice": "套餐价格每周一更新，请以当日报价为准。",
            "price_items": [
                ("月卡", "88.00", "仅限新用户首购"),
                ("季卡", "238.00", ""),
                ("年卡", "688.00", "含专属客服通道"),
            ],
            "tutorial_idx": [0, 1, 2, 3, 4],
            "phrase_idx": [3, 4, 5, 6, 7],
            "channels": ["汇通5329", "淘宝"],
            "note": "演示备注：套餐价 + 长列表",
        },
        "vbx": {
            "price_type": SKU.PRICE_TYPE_JPY_RECHARGE,
            "price_notice": "日元面额为平台标准档位，非自定义金额。",
            "price_items": [
                ("1000円", "52.00", ""),
                ("3000円", "148.00", "热门档位，库存紧张时请提前确认"),
                ("5000円", "245.00", ""),
            ],
            "tutorial_idx": [5],
            "phrase_idx": [0, 1],
            "channels": ["91卡券", "企业微信"],
            "note": "",
        },
    },
}


def purge_demo_platforms():
    deleted, _ = Platform.objects.filter(name__startswith=DEMO_PREFIX).delete()
    print(f"  已删除演示平台 {deleted} 条（级联业务/SKU）")


def ensure_tutorials():
    for i, (name, url) in enumerate(TUTORIAL_CATALOG):
        PaymentTutorial.objects.update_or_create(name=name, defaults={"detail_url": url, "sort_order": i * 10})
        TutorialPool.objects.update_or_create(name=name, defaults={"detail_url": url, "sort_order": i * 10})


def ensure_channel_tags():
    tags = {}
    for i, name in enumerate(CHANNEL_TAG_NAMES, start=1):
        tag, _ = Tag.objects.get_or_create(
            type=Tag.TYPE_CHANNEL,
            name=name,
            defaults={"order": i * 10},
        )
        tags[name] = tag
    return tags


def platform_tags_by_names(names):
    out = []
    for name in names:
        tag = Tag.objects.filter(type=Tag.TYPE_PLATFORM, name__iexact=name).first()
        if tag:
            out.append(tag)
    return out


def apply_sku_enrichment(sku, cfg, channel_map, tutorial_names):
    sku.status = cfg.get("status", SKU.STATUS_ON_SALE)
    sku.note = cfg.get("note", "")
    sku.price_type = cfg.get("price_type") or ""
    sku.price_notice = cfg.get("price_notice", "")
    sku.save(update_fields=["status", "note", "price_type", "price_notice"])

    sku.price_items.all().delete()
    for order, row in enumerate(cfg.get("price_items") or [], start=1):
        label, rmb, notice = row
        SKUPriceItem.objects.create(
            sku=sku,
            label=label,
            rmb_amount=Decimal(str(rmb)),
            notice=notice,
            sort_order=order * 10,
        )

    picked_t = [tutorial_names[i] for i in cfg.get("tutorial_idx", []) if i < len(tutorial_names)]
    sku.tutorial_text = " / ".join(picked_t)
    sku.save(update_fields=["tutorial_text"])

    sku.quick_phrases.all().delete()
    for order, idx in enumerate(cfg.get("phrase_idx", []), start=1):
        if idx < len(PHRASE_POOL):
            QuickPhrase.objects.create(sku=sku, order=order * 10, content=PHRASE_POOL[idx])

    channel_names = cfg.get("channels") or []
    sku.channel_tags.set([channel_map[n] for n in channel_names if n in channel_map])


def seed_demo_platforms(channel_map):
    tutorial_names = [t[0] for t in TUTORIAL_CATALOG]
    created_plat = 0
    created_sku = 0

    for spec in DEMO_PLATFORMS:
        platform, created = Platform.objects.get_or_create(
            name=spec["name"],
            defaults={
                "url": "https://example.com/demo",
                "status": spec["status"],
                "note": spec.get("note", ""),
                "sort_order": spec["sort_order"],
            },
        )
        if not created:
            platform.status = spec["status"]
            platform.note = spec.get("note", "")
            platform.sort_order = spec["sort_order"]
            platform.save(update_fields=["status", "note", "sort_order"])

        platform.platform_tags.set(platform_tags_by_names(spec.get("platform_tags") or []))
        if created:
            created_plat += 1

        for biz_spec in spec["businesses"]:
            business, _ = Business.objects.get_or_create(
                platform=platform,
                name=biz_spec["name"],
                defaults={"status": Platform.STATUS_ON_SALE},
            )
            for sku_spec in biz_spec["skus"]:
                sku, sku_created = SKU.objects.get_or_create(
                    business=business,
                    name=sku_spec["name"],
                    defaults={"status": sku_spec.get("status", SKU.STATUS_ON_SALE)},
                )
                apply_sku_enrichment(sku, sku_spec, channel_map, tutorial_names)
                if sku_created:
                    created_sku += 1

    return created_plat, created_sku


def enrich_legacy_platforms(channel_map):
    tutorial_names = [t[0] for t in TUTORIAL_CATALOG]
    updated = 0
    for platform_name, sku_map in LEGACY_SKU_ENRICH.items():
        platform = Platform.objects.filter(name=platform_name).first()
        if not platform:
            continue
        for sku_name, cfg in sku_map.items():
            sku = SKU.objects.filter(business__platform=platform, name=sku_name).first()
            if not sku:
                continue
            apply_sku_enrichment(sku, cfg, channel_map, tutorial_names)
            updated += 1
            print(f"  补全 {platform_name}/{sku_name}")
    return updated


def main():
    parser = argparse.ArgumentParser(description="写入本地职员端预览演示数据")
    parser.add_argument("--purge", action="store_true", help="先删除「演示·」平台再重建")
    args = parser.parse_args()

    if args.purge:
        purge_demo_platforms()

    print("写入教程模板…")
    ensure_tutorials()
    channel_map = ensure_channel_tags()

    print("创建演示平台…")
    n_plat, n_sku = seed_demo_platforms(channel_map)
    print(f"  新建平台 {n_plat} 个，新建 SKU {n_sku} 个")

    print("补全已有平台 SKU…")
    n_legacy = enrich_legacy_platforms(channel_map)

    total_plat = Platform.objects.count()
    total_biz = Business.objects.count()
    total_sku = SKU.objects.count()
    print(
        f"\n完成：数据库共 {total_plat} 平台、{total_biz} 业务、{total_sku} SKU；"
        f"本次补全旧数据 {n_legacy} 个 SKU。"
    )
    print("请刷新 http://localhost:5173/ 查看平台列表与商品详情。")


if __name__ == "__main__":
    main()
