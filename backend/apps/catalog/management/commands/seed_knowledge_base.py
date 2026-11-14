"""把现有商品上的「话术」和「教程」整理进「教程+话术」（只新增，不改动、不删除原来的数据）。

规则（按平台分别整理）：
  - 教程：档位引用的教程（按教程池里的名字找链接），加上话术里夹带的教程链接，同一篇只放一条。
  - 快捷语：话术里「要说的话」单独成一条，夹带的教程链接拆出来，改成「附带教程」
    （复制时会自动加在后面）；分点（1️⃣ 2️⃣…）各占一行；内容相同的只放一条，标题写上用到它的业务。
  - 教程池里没有被任何档位、话术用到的教程：放到「通用」里，之后可以在管理页改平台。
  - 问答：不导入（原来没有这类数据），在「教程+话术管理」里新增。
  - 已经导入过的（同平台、同类型、同链接 / 同内容）会跳过，所以重复执行也不会重复添加。

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
# 话术里「🔗链接」或飞书 / 金山文档链接当作教程；其他链接（比如设置页）留在话术里
LINK_RE = re.compile(r"(🔗\s*)?(https?://[^\s<>\"]+)")
DOC_HOSTS = ("feishu.cn", "kdocs.cn", "larksuite.com")


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _norm_url(u: str) -> str:
    return (u or "").strip().split("?")[0].split("#")[0].rstrip("/").lower()


def _norm_text(s: str) -> str:
    return re.sub(r"[\s。．.，,!！~～]+", "", s or "")


def _names(biz: list[str]) -> str:
    biz = list(OrderedDict.fromkeys(biz))
    t = "、".join(biz[:3])
    return t + (f" 等 {len(biz)} 个业务" if len(biz) > 3 else "")


def _format_notes(text: str) -> str:
    t = (text or "").replace("\xa0", " ").strip()
    t = re.sub(r"\s*([1-9]️⃣)", r"\n\1", t)        # 1️⃣ 2️⃣ … 各占一行
    t = re.sub(r"(?<=\S)\s+(\d)[:：]\s*", r"\n\1：", t)  # 「1: xxx 2: xxx」
    t = re.sub(r"\s*-{3,}\s*", "\n", t)
    t = re.sub(r"。{2,}", "。", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip(" \n")


def _title_of(notes: str) -> str:
    t = notes
    rules = [
        (lambda: "换ip登录" in t and "邮箱" in t, "账号交付注意（带邮箱）"),
        (lambda: "换ip登录" in t, "账号交付注意"),
        (lambda: "欧洲或美国ip" in t, "独享卡付款注意"),
        (lambda: "有效期" in t, "充值币有效期提醒"),
        (lambda: "虚拟卡密" in t, "卡密兑换提醒"),
        (lambda: "核对余额" in t, "充余额交付注意"),
        (lambda: "核对coban" in t, "coban 充值交付注意"),
        (lambda: "会员是否到账" in t, "会员交付注意"),
        (lambda: "换绑" in t, "换绑提醒"),
    ]
    for cond, name in rules:
        if cond():
            return name
    head = re.sub(r"\s+", " ", t).strip()
    return head[:16] + ("…" if len(head) > 16 else "")


def _split_phrase(text: str, pool_by_url: dict, pool_names: list[str]):
    """拆话术：返回 (要说的话, [(教程名, 链接)])。"""
    text = (text or "").replace("\xa0", " ")
    links = []
    for m in LINK_RE.finditer(text):
        url = m.group(2).rstrip("，。,.)）")
        is_doc = bool(m.group(1)) or any(h in url for h in DOC_HOSTS) or _norm_url(url) in pool_by_url
        if is_doc:
            links.append((m.start(), m.end(), url))
    if not links:
        return _format_notes(text), []
    tuts, prev, cut = [], 0, None
    for i, (start, end, url) in enumerate(links):
        seg = text[prev:start].rstrip()
        known = pool_by_url.get(_norm_url(url))
        name = None
        if i == 0:
            for n in ([known] if known else []) + pool_names:
                if n and _norm(seg).endswith(_norm(n)):
                    name = n
                    break
            if not name:
                name = seg.split(" ")[-1] if seg else ""
            # 名称在原文里的起点 = 要说的话的结尾
            first_word = (name.split(" ")[0] if name else "")
            idx = text.rfind(first_word, 0, start) if first_word else -1
            cut = idx if idx >= 0 else start
        else:
            name = seg.strip() or (known or "")
        name = (known if known and not name else name).strip() or "教程"
        tuts.append((name, url))
        prev = end
    notes = text[:cut]
    tail = text[prev:].strip()
    if tail:
        notes = notes.rstrip() + " " + tail
    return _format_notes(notes), tuts


def plan():
    """返回 (要新增的教程, 要新增的快捷语, 找不到链接的教程)。

    教程：[(platform 或 None, 名称, 链接)]
    快捷语：[(platform, 标题, 内容, [(教程名, 链接)])]
    """
    pool = OrderedDict((t.name.strip(), t.detail_url.strip()) for t in TutorialPool.objects.order_by("sort_order", "id")
                       if t.name and t.name.strip())
    pool_by_url = {_norm_url(u): n for n, u in pool.items() if u}
    pool_names = sorted(pool.keys(), key=len, reverse=True)

    have_tut, have_phr = set(), set()
    for e in KnowledgeEntry.objects.all():
        if e.kind == KnowledgeEntry.KIND_TUTORIAL:
            have_tut.add((e.platform_id, _norm_url(e.url)))
            have_tut.add((e.platform_id, "name:" + _norm(e.title)))
        elif e.kind == KnowledgeEntry.KIND_PHRASE:
            have_phr.add((e.platform_id, _norm_text(e.content)))

    tut_rows, phr_rows, missing, used = [], [], [], set()
    for p in Platform.objects.order_by("sort_order", "id"):
        tuts: OrderedDict[str, tuple] = OrderedDict()   # 链接 -> (名称, 链接)
        phrases: OrderedDict[str, dict] = OrderedDict()

        def add_tut(name, url):
            k = _norm_url(url)
            if k not in tuts:
                tuts[k] = (name, url)
            used.add(name)
            used.add(pool_by_url.get(k, ""))

        skus = SKU.objects.filter(business__platform=p).select_related("business").prefetch_related("quick_phrases")
        for s in skus.order_by("business_id", "id"):
            for n in (s.tutorial_text or "").split(TUTORIAL_SEP):
                n = n.strip()
                if not n:
                    continue
                if pool.get(n):
                    add_tut(n, pool[n])
                else:
                    missing.append(f"{p.name} › {n}")
            for ph in s.quick_phrases.all():
                notes, links = _split_phrase(ph.content, pool_by_url, pool_names)
                for name, url in links:
                    add_tut(pool_by_url.get(_norm_url(url)) or name, url)
                if not notes:
                    continue
                d = phrases.setdefault(_norm_text(notes), {"notes": notes, "biz": [], "links": OrderedDict()})
                d["biz"].append(s.business.name)
                for name, url in links:
                    d["links"].setdefault(_norm_url(url), (pool_by_url.get(_norm_url(url)) or name, url))

        for k, (name, url) in tuts.items():
            if (p.id, k) in have_tut or (p.id, "name:" + _norm(name)) in have_tut:
                continue
            tut_rows.append((p, name, url))
        for k, d in phrases.items():
            if (p.id, k) in have_phr:
                continue
            title = f"{_title_of(d['notes'])}（{_names(d['biz'])}）"
            phr_rows.append((p, title, d["notes"], list(d["links"].values())))

    for n, url in pool.items():
        if n in used or not url:
            continue
        if (None, _norm_url(url)) in have_tut:
            continue
        tut_rows.append((None, n, url))
    return tut_rows, phr_rows, missing


class Command(BaseCommand):
    help = "把现有商品上的话术和教程导入「教程+话术」。默认试运行，加 --apply 才会写入。"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="正式导入")

    def handle(self, *args, **opts):
        tut_rows, phr_rows, missing = plan()
        by: OrderedDict[str, list] = OrderedDict()
        for p, name, _u in tut_rows:
            by.setdefault(p.name if p else "通用", []).append(f"[教程] {name}")
        for p, title, _c, links in phr_rows:
            extra = f"（附带 {len(links)} 个教程）" if links else ""
            by.setdefault(p.name, []).append(f"[快捷语] {title}{extra}")
        for name, items in by.items():
            self.stdout.write(self.style.MIGRATE_HEADING(f"{name}（{len(items)} 条）"))
            for it in items:
                self.stdout.write("  " + it)
        if missing:
            self.stdout.write(self.style.WARNING("\n这些教程在教程池里找不到链接，没有导入："))
            for m in OrderedDict.fromkeys(missing):
                self.stdout.write("  " + m)
        self.stdout.write(f"\n合计：教程 {len(tut_rows)} 条，快捷语 {len(phr_rows)} 条。"
                          "原来商品上的话术、教程和教程池都不会改动。")
        if not opts["apply"]:
            self.stdout.write(self.style.WARNING("这是试运行，什么都没写。确认无误后加 --apply 正式导入。"))
            return
        with transaction.atomic():
            ids: dict[tuple, int] = {}
            for e in KnowledgeEntry.objects.filter(kind=KnowledgeEntry.KIND_TUTORIAL):
                ids[(e.platform_id, _norm_url(e.url))] = e.id
            for i, (p, name, url) in enumerate(tut_rows):
                e = KnowledgeEntry.objects.create(platform=p, kind=KnowledgeEntry.KIND_TUTORIAL, title=name[:300],
                                                  url=url, sort_order=i)
                ids[(e.platform_id, _norm_url(url))] = e.id
            for i, (p, title, notes, links) in enumerate(phr_rows):
                att = [ids[(p.id, _norm_url(u))] for _n, u in links if (p.id, _norm_url(u)) in ids]
                KnowledgeEntry.objects.create(platform=p, kind=KnowledgeEntry.KIND_PHRASE, title=title[:300],
                                              content=notes, tutorials=list(dict.fromkeys(att)), sort_order=i)
        self.stdout.write(self.style.SUCCESS(f"✓ 已导入：教程 {len(tut_rows)} 条，快捷语 {len(phr_rows)} 条。"))
