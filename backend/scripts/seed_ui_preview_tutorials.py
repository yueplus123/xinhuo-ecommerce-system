"""一次性写入 UI 预览用教程/快捷语假数据（仅本地 fghdg 平台）。"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from backend.apps.catalog.models import PaymentTutorial, Platform, QuickPhrase, SKU, TutorialPool

FAKE_TUTORIALS = [
    ("PayPal 跨境支付流程", "https://example.com/tutorial/paypal-flow"),
    ("Fanbox 订阅开通指南", "https://example.com/tutorial/fanbox-guide"),
    ("信用卡 3DS 验证说明", "https://example.com/tutorial/3ds-verify"),
    ("代充失败排错步骤", "https://example.com/tutorial/troubleshoot"),
    ("退款与售后处理规范", "https://example.com/tutorial/refund-policy"),
    ("新用户首单操作教程", "https://example.com/tutorial/first-order"),
    ("海外账号绑定注意事项（含多步骤图文）", "https://example.com/tutorial/account-bind-long-title"),
]

SKU_PREVIEW = {
    "vfdb": {
        "tutorial_idx": [0, 1, 2],
        "phrases": [
            "您好，订单已收到，正在为您处理中，请稍候。",
            "支付成功后请截图回传，方便核验到账。",
            "教程已发送，请按步骤操作；如遇 3DS 验证请留意短信。",
        ],
        "note": "演示备注：该 SKU 含 3 条教程 + 3 条快捷语",
    },
    "42542": {
        "tutorial_idx": [0, 1, 2, 3, 4],
        "phrases": [
            "请勿重复下单，避免重复扣费。",
            "当前高峰期预计 15-30 分钟处理完成。",
            "若支付失败，请优先更换浏览器或开启无痕模式重试。",
            "如出现风控提示，请截图联系客服协助处理。",
            "发货完成后会在企业微信推送通知，请注意查收。",
        ],
        "note": "演示备注：5 条教程 + 5 条快捷语，用于测试长列表折叠",
    },
    "vbx": {
        "tutorial_idx": [5],
        "phrases": [
            "本 SKU 为单教程演示，点击「教程 (1)」可展开查看。",
            "快捷语也可一键复制发送给客户。",
        ],
        "note": "",
    },
}


def main():
    for i, (name, url) in enumerate(FAKE_TUTORIALS):
        PaymentTutorial.objects.update_or_create(name=name, defaults={"detail_url": url, "sort_order": i * 10})
        TutorialPool.objects.update_or_create(name=name, defaults={"detail_url": url, "sort_order": i * 10})

    platform = Platform.objects.filter(name="fghdg").first()
    if not platform:
        print("未找到平台 fghdg，跳过。")
        return

    names = [t[0] for t in FAKE_TUTORIALS]
    updated = 0
    for sku in SKU.objects.filter(business__platform=platform):
        cfg = SKU_PREVIEW.get(sku.name)
        if not cfg:
            continue
        picked = [names[i] for i in cfg["tutorial_idx"]]
        sku.tutorial_text = " / ".join(picked)
        sku.note = cfg.get("note") or sku.note
        sku.save(update_fields=["tutorial_text", "note"])

        sku.quick_phrases.all().delete()
        for order, content in enumerate(cfg["phrases"], start=1):
            QuickPhrase.objects.create(sku=sku, order=order * 10, content=content)
        updated += 1
        print(f"  SKU {sku.name}: 教程 {len(picked)} 条, 快捷语 {len(cfg['phrases'])} 条")

    print(f"完成：写入 {len(FAKE_TUTORIALS)} 条教程模板，更新 {updated} 个 SKU。")


if __name__ == "__main__":
    main()
