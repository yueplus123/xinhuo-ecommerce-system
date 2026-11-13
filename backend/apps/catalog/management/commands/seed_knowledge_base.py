"""把现有商品上的「话术」和「教程」整理进「教程+话术」知识库（只新增，不改动、不删除原来的数据）。

规则：
  - 快捷语：每个平台下所有档位的话术，内容相同的只放一条；标题写上用到它的业务名和内容开头。
  - 教程：每个平台下所有档位引用的教程（按教程池里的名字找链接），同一篇只放一条。
  - 教程池里没有被任何档位用到的教程：放到「通用」里，之后可以在页面上改平台。
  - 已经导入过的（同平台、同类型、同内容 / 同链接）会跳过，所以重复执行也不会重复添加。

用法（在 /var/www/xinhuo/app 下）：
  PYTHONPATH=. .venv/bin/python backend/manage.py seed_knowledge_base           # 试运行：只显示会加什么
  PYTHONPATH=. .venv/bin/python backend/manage.py seed_knowledge_base --apply   # 正式导入
"""

from __future__ import annotations

import re
from collections import OrderedDict

from django.core.management.base import BaseCommand
from django.db import transaction

from backend.apps.catalog.models import SKU, KnowledgeEntry, Platform, TutorialPool

TUTORIAL_SEP = " / "  # 与 manage_sku._TUTORIAL_SEP 一致


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _head(text: str) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    return t[:18] + ("…" if len(t) > 18 else "")


def _names(biz: list[str]) -> str:
    biz = list(OrderedDict.fromkeys(biz))
    t = "、".join(biz[:3])
    return t + (f" 等 {len(biz)} 个业务" if len(biz) > 3 else "")


def plan():
    """返回 [(platform 或 None, kind, title, content, url)]，已存在的不包含。"""
    pool = OrderedDict((t.name.strip(), t.detail_url) for t in TutorialPool.objects.order_by("sort_order", "id"))
    existing = set()
    for e in KnowledgeEntry.objects.all():
        key = _norm(e.url) if e.kind == KnowledgeEntry.KIND_TUTORIAL else _norm(e.content)
        existing.add((e.platform_id, e.kind, key))
        if e.kind == KnowledgeEntry.KIND_TUTORIAL:
            existing.add((e.platform_id, e.kind, "name:" + _norm(e.title)))

    rows, used_tutorials, missing = [], set(), []
    for p in Platform.objects.order_by("sort_order", "id"):
        phrases: OrderedDict[str, dict] = OrderedDict()
        tutorials: OrderedDict[str, list] = OrderedDict()
        skus = SKU.objects.filter(business__platform=p).select_related("business").prefetch_related("quick_phrases")
        for s in skus.order_by("business_id", "id"):
            for ph in s.quick_phrases.all():
                text = (ph.content or "").strip()
                if not text:
                    continue
                d = phrases.setdefault(_norm(text), {"text": text, "biz": []})
                d["biz"].append(s.business.name)
            for n in (s.tutorial_text or "").split(TUTORIAL_SEP):
                n = n.strip()
                if n:
                    tutorials.setdefault(n, []).append(s.business.name)
        for k, d in phrases.items():
            if (p.id, KnowledgeEntry.KIND_PHRASE, k) not in existing:
                rows.append((p, KnowledgeEntry.KIND_PHRASE, _names(d["biz"]) + " · " + _head(d["text"]), d["text"], ""))
        for n, biz in tutorials.items():
            used_tutorials.add(n)
            url = pool.get(n, "")
            if not url:
                missing.append(f"{p.name} › {n}")
                continue
            if (p.id, KnowledgeEntry.KIND_TUTORIAL, _norm(url)) in existing or \
               (p.id, KnowledgeEntry.KIND_TUTORIAL, "name:" + _norm(n)) in existing:
                continue
            rows.append((p, KnowledgeEntry.KIND_TUTORIAL, n, "", url))
    for n, url in pool.items():
        if n in used_tutorials or not url:
            continue
        if (None, KnowledgeEntry.KIND_TUTORIAL, _norm(url)) in existing:
            continue
        rows.append((None, KnowledgeEntry.KIND_TUTORIAL, n, "", url))
    return rows, missing


class Command(BaseCommand):
    help = "把现有商品上的话术和教程导入「教程+话术」知识库。默认试运行，加 --apply 才会写入。"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="正式导入")

    def handle(self, *args, **opts):
        rows, missing = plan()
        by: OrderedDict[str, list] = OrderedDict()
        for p, kind, title, _c, _u in rows:
            by.setdefault(p.name if p else "通用", []).append((kind, title))
        label = dict(KnowledgeEntry.KIND_CHOICES)
        for name, items in by.items():
            self.stdout.write(self.style.MIGRATE_HEADING(f"{name}（{len(items)} 条）"))
            for kind, title in items:
                self.stdout.write(f"  [{label[kind]}] {title}")
        if missing:
            self.stdout.write(self.style.WARNING("\n这些教程在教程池里找不到链接，没有导入："))
            for m in missing:
                self.stdout.write("  " + m)
        n_ph = sum(1 for r in rows if r[1] == KnowledgeEntry.KIND_PHRASE)
        n_tu = len(rows) - n_ph
        self.stdout.write(f"\n合计：快捷语 {n_ph} 条，教程 {n_tu} 条。原来商品上的话术和教程不会改动。")
        if not opts["apply"]:
            self.stdout.write(self.style.WARNING("这是试运行，什么都没写。确认无误后加 --apply 正式导入。"))
            return
        with transaction.atomic():
            for i, (p, kind, title, content, url) in enumerate(rows):
                KnowledgeEntry.objects.create(platform=p, kind=kind, title=title[:300], content=content, url=url,
                                              sort_order=i)
        self.stdout.write(self.style.SUCCESS(f"✓ 已导入 {len(rows)} 条。"))
