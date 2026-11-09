"""值班打卡后推送企业微信群（群机器人 Webhook，只支持内部群）。

环境变量（写在项目根目录 .env，不要提交到 GitHub）：
  DUTY_WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...
  STAFF_FRONTEND_BASE_URL=http://...   # 截图链接用的站点地址
没填 Webhook 就不推送。推送在后台线程里做，不会拖慢打卡。
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from .wecom_webhook import WecomWebhookError, send_markdown

logger = logging.getLogger(__name__)
_WD = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def webhook_url() -> str:
    return (os.environ.get("DUTY_WECOM_WEBHOOK_URL") or "").strip()


def _site() -> str:
    base = (getattr(settings, "STAFF_FRONTEND_BASE_URL", None) or "").strip().rstrip("/")
    return "" if (not base or "localhost" in base or "127.0.0.1" in base) else base


def _when(dt: datetime) -> str:
    lt = timezone.localtime(dt)
    return f"{lt.month}月{lt.day}日 {_WD[lt.weekday()]} {lt:%H:%M}"


def build_checkin_markdown(*, task, rec, doer_name: str, assignee_name: str, cover_for_name: str = "",
                           target=None, progress: tuple[int, int] | None = None, remaining: list[str] | None = None,
                           edited: bool = False) -> str:
    d = rec.data or {}
    title = f"**✅ {'修改打卡' if edited else '已打卡'} · {task.icon or '📌'} {task.name}**"
    lines = [title]
    who = f'<font color="info">{assignee_name}</font>'
    if doer_name and doer_name != assignee_name:
        who += f"（{doer_name} 代为打卡）"
    if cover_for_name:
        who += f"　<font color=\"comment\">代 {cover_for_name} 的班</font>"
    lines.append(f"> 打卡人：{who}")
    lines.append(f"> 时间：{_when(rec.edited_at or rec.done_at)}")
    if task.qty_enabled and d.get("qty") is not None:
        label = task.qty_label or "数量"
        q = f"> {label}：**{d['qty']}** {task.qty_unit}".rstrip()
        if target is not None:
            if d["qty"] >= target:
                q += f"（目标 {target} ✓）"
            else:
                q += f'（目标 {target}，<font color="warning">还差 {target - d["qty"]}</font>）'
        lines.append(q)
    checks = d.get("checks") or {}
    if task.checklist:
        lines.append("> 清单：" + "　".join(("✓ " if checks.get(str(i)) else "✗ ") + c for i, c in enumerate(task.checklist)))
    if d.get("note"):
        lines.append(f"> 备注：{str(d['note'])[:200]}")
    if rec.image:
        site = _site()
        lines.append(f"> [📷 查看截图]({site}{rec.image.url})" if site else "> 📷 已上传截图（在系统里查看）")
    if progress:
        done, total = progress
        tail = f"今日进度：**{done}/{total}**"
        if remaining:
            tail += f'　<font color="warning">还剩：{"、".join(remaining[:6])}{" 等" if len(remaining) > 6 else ""}</font>'
        else:
            tail += "　🎉 今天的事都做完了"
        lines += ["", tail]
    return "\n".join(lines)


def push_async(markdown: str) -> None:
    url = webhook_url()
    if not url:
        return

    def _run():
        try:
            send_markdown(url, markdown)
        except WecomWebhookError as e:
            logger.warning("值班打卡推送失败：%s", e)
        except Exception:  # noqa: BLE001
            logger.exception("值班打卡推送异常")

    threading.Thread(target=_run, daemon=True).start()
