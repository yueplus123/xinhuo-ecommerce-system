"""一次性整理：Fanbox / Pixiv 的业务和档位（SKU）归属（2026-11-10 按老板确认的结构）。

目标结构：
  Fanbox
    fanbox代赞助：充值pixivcoban（5 档）、一次性卡、共享fanbox号、赞助卡（原「fanbox独享visa卡」）、fanbox作品下载（原「打包下载」）
    fanbox账号：不变
  Pixiv
    pixiv高级会员：1 个月（原「一个月高级会员」）、3 / 6 / 12 个月
    pixiv画师约稿：不变（加 --rename 时改名为「pixiv画师赞助」）
  booth：不变（加 --rename 时「代开visa卡订阅支付booth」改名为「代开visa订阅booth」）

挪空的业务改为「禁售」（不删除，随时可以在后台改回来）。
档位只是换了所属业务，价格、话术、教程、截图、渠道标签都跟着档位走，不会丢。

用法（在 /var/www/xinhuo/app 下）：
  PYTHONPATH=. .venv/bin/python backend/manage.py reorg_catalog_20261110            # 试运行：只显示会改什么
  PYTHONPATH=. .venv/bin/python backend/manage.py reorg_catalog_20261110 --apply    # 先自动备份数据库，再正式执行
  可再加 --rename：顺便改两个业务名称（见上）

安全检查：执行前逐个核对档位 / 业务的 id 和名称，和线上不一致就整体放弃，什么都不改。
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from backend.apps.catalog.models import SKU, Business

# (档位 id, 档位名称, 原业务 id, 原业务名称, 目标业务 id, 目标业务名称)
MOVES = [
    (2405, "1000日元", 167, "充值pixivcoban币", 163, "fanbox代赞助"),
    (2406, "2000日元", 167, "充值pixivcoban币", 163, "fanbox代赞助"),
    (2407, "3000日元", 167, "充值pixivcoban币", 163, "fanbox代赞助"),
    (2408, "5000日元", 167, "充值pixivcoban币", 163, "fanbox代赞助"),
    (2409, "10000日元", 167, "充值pixivcoban币", 163, "fanbox代赞助"),
    (2411, "赞助卡", 164, "fanbox独享visa卡", 163, "fanbox代赞助"),
    (2410, "fanbox作品下载", 166, "打包下载", 163, "fanbox代赞助"),
    (2417, "1个月会员", 170, "一个月高级会员", 168, "pixiv高级会员"),
]
# 挪完后应该变空、改为禁售的业务
EMPTY_AFTER = [(164, "fanbox独享visa卡"), (166, "打包下载"), (167, "充值pixivcoban币"), (170, "一个月高级会员")]
# --rename 时改名：(业务 id, 现在的名字, 新名字)
RENAMES = [(171, "pixiv画师约稿", "pixiv画师赞助"), (174, "代开visa卡订阅支付booth", "代开visa订阅booth")]
# 只核对、不改动（确认结构和预期一致）
KEEP = [(163, "fanbox代赞助", 23), (165, "fanbox账号", 23), (168, "pixiv高级会员", 24), (171, None, 24),
        (172, "代购booth商品", 25), (173, "充值pixivcoban币", 25), (174, None, 25)]


def _same(a: str, b: str) -> bool:
    return (a or "").replace(" ", "").strip() == (b or "").replace(" ", "").strip()


class Command(BaseCommand):
    help = "整理 Fanbox / Pixiv 的业务和档位归属（2026-11-10）。默认试运行，加 --apply 才会真正修改。"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="正式执行（会先备份数据库）")
        parser.add_argument("--rename", action="store_true", help="顺便改两个业务名称")
        parser.add_argument("--no-backup", action="store_true", help="不备份（仅测试用）")

    def handle(self, *args, **opts):
        problems = self._check(opts["rename"])
        if problems:
            for p in problems:
                self.stdout.write(self.style.ERROR("✗ " + p))
            raise CommandError("线上数据和预期不一致，已放弃，什么都没改。把上面的输出发给开发看一下。")

        self.stdout.write(self.style.MIGRATE_HEADING("将要做的修改："))
        for sid, sname, fb, fbn, tb, tbn in MOVES:
            self.stdout.write(f"  挪档位  #{sid}「{sname}」：{fbn}（#{fb}） → {tbn}（#{tb}）")
        for bid, bname in EMPTY_AFTER:
            self.stdout.write(f"  停用业务 #{bid}「{bname}」（挪空后改为禁售，不删除）")
        if opts["rename"]:
            for bid, old, new in RENAMES:
                self.stdout.write(f"  改名业务 #{bid}「{old}」 → 「{new}」")

        if not opts["apply"]:
            self.stdout.write("")
            self._print_tree("整理后的样子（预览）", preview=True, rename=opts["rename"])
            self.stdout.write(self.style.WARNING("\n这是试运行，什么都没改。确认无误后加 --apply 正式执行。"))
            return

        if not opts["no_backup"]:
            self._backup()
        with transaction.atomic():
            for sid, _sname, _fb, _fbn, tb, _tbn in MOVES:
                SKU.objects.filter(pk=sid).update(business_id=tb)
            for bid, _ in EMPTY_AFTER:
                if SKU.objects.filter(business_id=bid).exists():
                    raise CommandError(f"业务 #{bid} 挪完后还有档位，已回滚，什么都没改。")
                Business.objects.filter(pk=bid).update(status=Business.STATUS_OFF_SALE)
            if opts["rename"]:
                for bid, _old, new in RENAMES:
                    Business.objects.filter(pk=bid).update(name=new)
        self.stdout.write("")
        self._print_tree("整理后的样子", preview=False, rename=opts["rename"])
        self.stdout.write(self.style.SUCCESS("\n✓ 已完成。刷新职员端「平台/商品」就能看到。"))

    # ---------------- 检查 ----------------
    def _check(self, rename: bool) -> list[str]:
        out = []
        biz = {b.id: b for b in Business.objects.filter(pk__in={m[2] for m in MOVES} | {m[4] for m in MOVES}
                                                           | {k[0] for k in KEEP} | {e[0] for e in EMPTY_AFTER})}
        for bid, name, pid in KEEP:
            b = biz.get(bid)
            if not b:
                out.append(f"找不到业务 #{bid}")
            elif name and not _same(b.name, name):
                out.append(f"业务 #{bid} 现在叫「{b.name}」，预期是「{name}」")
            elif b.platform_id != pid:
                out.append(f"业务 #{bid}「{b.name}」不在预期的平台 #{pid} 下")
        for sid, sname, fb, fbn, tb, tbn in MOVES:
            s = SKU.objects.filter(pk=sid).first()
            if not s:
                out.append(f"找不到档位 #{sid}「{sname}」")
                continue
            if not _same(s.name, sname):
                out.append(f"档位 #{sid} 现在叫「{s.name}」，预期是「{sname}」")
            if s.business_id != fb:
                out.append(f"档位 #{sid}「{s.name}」现在在业务 #{s.business_id}，预期在 #{fb}「{fbn}」（可能已经整理过了）")
            for bid, bname in ((fb, fbn), (tb, tbn)):
                b = biz.get(bid)
                if not b:
                    out.append(f"找不到业务 #{bid}「{bname}」")
                elif not _same(b.name, bname):
                    out.append(f"业务 #{bid} 现在叫「{b.name}」，预期是「{bname}」")
            if biz.get(fb) and biz.get(tb) and biz[fb].platform_id != biz[tb].platform_id:
                out.append(f"档位 #{sid} 的原业务和目标业务不在同一个平台")
        moving = {m[0] for m in MOVES}
        for bid, bname in EMPTY_AFTER:
            left = list(SKU.objects.filter(business_id=bid).exclude(pk__in=moving).values_list("id", "name"))
            if left:
                out.append(f"业务 #{bid}「{bname}」里还有清单外的档位：{left}，挪完不会变空")
        if rename:
            for bid, old, _new in RENAMES:
                b = Business.objects.filter(pk=bid).first()
                if not b or not _same(b.name, old):
                    out.append(f"要改名的业务 #{bid} 现在不叫「{old}」")
        return out

    # ---------------- 展示 ----------------
    def _print_tree(self, title: str, *, preview: bool, rename: bool):
        self.stdout.write(self.style.MIGRATE_HEADING(title + "："))
        target = {m[0]: m[4] for m in MOVES}
        off = {e[0] for e in EMPTY_AFTER}
        new_name = {r[0]: r[2] for r in RENAMES} if rename else {}
        for pid, pname in ((23, "Fanbox"), (24, "Pixiv"), (25, "booth")):
            self.stdout.write(f"  {pname}")
            for b in Business.objects.filter(platform_id=pid).order_by("id"):
                skus = [s for s in SKU.objects.filter(business__platform_id=pid).order_by("id")
                        if (target.get(s.id, s.business_id) if preview else s.business_id) == b.id]
                status = "禁售" if (preview and b.id in off) or b.status == Business.STATUS_OFF_SALE else ""
                name = new_name.get(b.id, b.name) if preview else b.name
                self.stdout.write(f"    {name}{'（' + status + '）' if status else ''}")
                for s in skus:
                    self.stdout.write(f"      - {s.name}")

    def _backup(self):
        db = Path(settings.DATABASES["default"]["NAME"])
        if not db.exists():
            raise CommandError(f"找不到数据库文件 {db}，为安全起见没有执行")
        dst = db.with_name(db.name + f".bak-reorg-{datetime.now():%Y%m%d-%H%M%S}")
        shutil.copy2(db, dst)
        self.stdout.write(self.style.SUCCESS(f"已备份数据库：{dst}"))
        self.stdout.write(f"  出问题时恢复：systemctl stop xinhuo-backend && cp {dst} {db} && systemctl start xinhuo-backend")
