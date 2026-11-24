"""邮件推送（QQ 邮箱 → 企微群）管理接口，仅超级管理员（管理后台「邮件推送」页）。

GET    /api/mail-push/                    总览：设置、邮箱状态、规则、今日统计
PATCH  /api/mail-push/settings/           改设置（Webhook、观察模式、间隔、摘要字数、排除规则）
POST   /api/mail-push/accounts/           添加邮箱
PATCH  /api/mail-push/accounts/<id>/      修改邮箱（授权码留空 = 不修改）
DELETE /api/mail-push/accounts/<id>/      删除邮箱（连同它的推送记录）
POST   /api/mail-push/accounts/test/      测试登录（{id} 或 {email, auth_code}）
POST   /api/mail-push/rules/              新建规则
PATCH  /api/mail-push/rules/<id>/         修改规则
DELETE /api/mail-push/rules/<id>/         删除规则
POST   /api/mail-push/preview/            规则的群消息预览（示例邮件）
GET    /api/mail-push/records/            推送记录 ?status=&q=&account=
POST   /api/mail-push/records/<id>/retry/ 重新推送
POST   /api/mail-push/check-now/          让收信服务立即检查一轮
POST   /api/mail-push/test-push/          发测试消息到企微群

授权码只写不读：接口永远不返回授权码，只返回 has_auth_code。
"""

from __future__ import annotations

import re

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.catalog import mail_push
from backend.apps.catalog import mail_push_engine as eng
from backend.apps.catalog.models import MailPushAccount, MailPushRecord, MailPushRule, MailPushSettings


class _SuperuserOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_superuser)


def _bad(msg: str, status: int = 400) -> Response:
    return Response({"detail": msg}, status=status)


def _iso(dt):
    return dt.isoformat() if dt else None


def _settings_payload(s: MailPushSettings) -> dict:
    return {
        "webhook_url": mail_push.mask_webhook(s.webhook_url),
        "has_webhook": bool(s.webhook_url),
        "dry_run": s.dry_run,
        "poll_interval": s.poll_interval,
        "summary_chars": s.summary_chars,
        "exclude_senders": mail_push.split_lines(s.exclude_senders),
        "exclude_keywords": mail_push.split_lines(s.exclude_keywords),
        "worker_alive": mail_push.worker_alive(s),
        "worker_heartbeat_at": _iso(s.worker_heartbeat_at),
        "last_round_at": _iso(s.last_round_at),
        "check_pending": bool(s.check_requested_at and (not s.last_round_at or s.check_requested_at > s.last_round_at)),
    }


def _account_payload(a: MailPushAccount, today: dict) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "email": a.email,
        "has_auth_code": bool(a.auth_code),
        "enabled": a.enabled,
        "last_check_at": _iso(a.last_check_at),
        "last_ok": a.last_ok,
        "last_error": a.last_error,
        "fail_count": a.fail_count,
        "today": today,
    }


def _rule_payload(r: MailPushRule, hits: int = 0) -> dict:
    accs = list(r.accounts.all())
    return {
        "id": r.id,
        "name": r.name,
        "senders": mail_push.split_lines(r.senders),
        "subject_keywords": mail_push.split_lines(r.subject_keywords),
        "style": r.style,
        "account_ids": [a.id for a in accs],
        "account_names": [a.name for a in accs],
        "enabled": r.enabled,
        "sort_order": r.sort_order,
        "today_hits": hits,
    }


def build_overview() -> dict:
    s = MailPushSettings.load()
    today_qs = MailPushRecord.objects.filter(created_at__date=timezone.localdate())
    per_account: dict[int, dict] = {}
    today_total: dict[str, int] = {}
    for row in today_qs.values("account_id", "status").annotate(n=Count("id")):
        per_account.setdefault(row["account_id"], {})[row["status"]] = row["n"]
        today_total[row["status"]] = today_total.get(row["status"], 0) + row["n"]
    hits = {
        row["rule_name"]: row["n"]
        for row in today_qs.filter(status__in=("pushed", "dry_run", "failed"))
        .values("rule_name")
        .annotate(n=Count("id"))
    }
    counts = {row["status"]: row["n"] for row in MailPushRecord.objects.values("status").annotate(n=Count("id"))}
    return {
        "settings": _settings_payload(s),
        "accounts": [_account_payload(a, per_account.get(a.id, {})) for a in MailPushAccount.objects.all()],
        "rules": [_rule_payload(r, hits.get(r.name, 0)) for r in MailPushRule.objects.prefetch_related("accounts")],
        "today": today_total,
        "counts": counts,
    }


class MailPushOverviewAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def get(self, request):
        return Response(build_overview())


class MailPushSettingsAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def patch(self, request):
        d = request.data or {}
        s = MailPushSettings.load()
        fields = []
        if "webhook_url" in d:
            w = str(d.get("webhook_url") or "").strip()
            if w != mail_push.mask_webhook(s.webhook_url):     # 页面显示的是打码地址，没改就不动
                if w and not w.startswith(mail_push.WEBHOOK_PREFIX):
                    return _bad(f"Webhook 地址应该以 {mail_push.WEBHOOK_PREFIX} 开头")
                s.webhook_url = w
                fields.append("webhook_url")
        if "dry_run" in d:
            s.dry_run = bool(d.get("dry_run"))
            fields.append("dry_run")
        for key, lo, hi, label in (("poll_interval", 30, 3600, "检查间隔"), ("summary_chars", 50, 1500, "摘要字数")):
            if key in d:
                try:
                    v = int(d.get(key))
                except (TypeError, ValueError):
                    return _bad(f"{label}要填数字")
                if not lo <= v <= hi:
                    return _bad(f"{label}要在 {lo} 到 {hi} 之间")
                setattr(s, key, v)
                fields.append(key)
        if "exclude_senders" in d:
            s.exclude_senders = "\n".join(x.lower() for x in mail_push.split_lines(d.get("exclude_senders")))
            fields.append("exclude_senders")
        if "exclude_keywords" in d:
            s.exclude_keywords = "\n".join(mail_push.split_lines(d.get("exclude_keywords")))
            fields.append("exclude_keywords")
        if fields:
            s.save(update_fields=[*fields, "updated_at"])
        return Response(build_overview())


_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}")


def _clean_code(v) -> str:
    return re.sub(r"\s+", "", str(v or ""))


class MailPushAccountListAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def post(self, request):
        d = request.data or {}
        name = str(d.get("name") or "").strip()
        email = str(d.get("email") or "").strip().lower()
        code = _clean_code(d.get("auth_code"))
        if not name:
            return _bad("请填写名称")
        if not _EMAIL_RE.fullmatch(email):
            return _bad("邮箱地址格式不对")
        if not code:
            return _bad("请填写授权码")
        if MailPushAccount.objects.filter(name=name).exists():
            return _bad("名称和其他邮箱重复了")
        if MailPushAccount.objects.filter(email=email).exists():
            return _bad("这个邮箱已经添加过了")
        a = MailPushAccount.objects.create(
            name=name[:30], email=email, auth_code=code[:100], enabled=bool(d.get("enabled", True)),
            sort_order=MailPushAccount.objects.count(),
        )
        return Response(_account_payload(a, {}), status=201)


class MailPushAccountDetailAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def patch(self, request, pk: int):
        a = MailPushAccount.objects.filter(pk=pk).first()
        if not a:
            return _bad("邮箱不存在", 404)
        d = request.data or {}
        if "name" in d:
            name = str(d.get("name") or "").strip()
            if not name:
                return _bad("请填写名称")
            if MailPushAccount.objects.filter(name=name).exclude(pk=pk).exists():
                return _bad("名称和其他邮箱重复了")
            a.name = name[:30]
        if "email" in d:
            email = str(d.get("email") or "").strip().lower()
            if not _EMAIL_RE.fullmatch(email):
                return _bad("邮箱地址格式不对")
            if MailPushAccount.objects.filter(email=email).exclude(pk=pk).exists():
                return _bad("这个邮箱已经添加过了")
            if email != a.email:            # 换了邮箱：从新邮箱的当前位置重新开始，不推历史邮件
                a.email, a.uidvalidity, a.last_uid = email, None, None
                a.last_ok, a.last_error, a.fail_count = None, "", 0
        code = _clean_code(d.get("auth_code"))
        if code:
            a.auth_code = code[:100]
        if "enabled" in d:
            a.enabled = bool(d.get("enabled"))
        a.save()
        return Response(_account_payload(a, {}))

    def delete(self, request, pk: int):
        deleted, _ = MailPushAccount.objects.filter(pk=pk).delete()
        if not deleted:
            return _bad("邮箱不存在", 404)
        return Response(status=204)


class MailPushAccountTestAPIView(APIView):
    """测试登录；编辑已有邮箱时授权码可以不填（用已保存的）。"""

    permission_classes = [_SuperuserOnly]

    def post(self, request):
        d = request.data or {}
        email = str(d.get("email") or "").strip().lower()
        code = _clean_code(d.get("auth_code"))
        if d.get("id") and (not code or not email):
            a = MailPushAccount.objects.filter(pk=d.get("id")).first()
            if a:
                email = email or a.email
                code = code or a.auth_code
        if not email or not code:
            return _bad("请填写邮箱地址和授权码")
        try:
            count = eng.check_login(email, code)
        except Exception as e:
            return _bad(str(e)[:300])
        return Response({"ok": True, "detail": f"登录成功，收件箱共 {count} 封邮件"})


def _rule_from_request(d, rule: MailPushRule | None = None):
    """校验并写入规则字段，返回 (rule, account_ids) 或抛 ValueError。"""
    rule = rule or MailPushRule()
    if "name" in d or rule.pk is None:
        name = str(d.get("name") or "").strip()
        if not name:
            raise ValueError("请填写规则名称")
        rule.name = name[:30]
    senders = mail_push.split_lines(d["senders"] if "senders" in d else rule.senders)
    senders = [x.lower() for x in senders]
    kws = mail_push.split_lines(d["subject_keywords"] if "subject_keywords" in d else rule.subject_keywords)
    if not senders and not kws:
        raise ValueError("发件人和标题关键词至少要填一项，不然所有邮件都会被推送")
    for s in senders:
        if "@" not in s:
            raise ValueError(f"发件人「{s}」格式不对：填完整邮箱，或 @域名")
    rule.senders, rule.subject_keywords = "\n".join(senders), "\n".join(kws)
    if "style" in d:
        if d.get("style") not in mail_push.STYLES:
            raise ValueError("推送样式不对")
        rule.style = d["style"]
    if "enabled" in d:
        rule.enabled = bool(d.get("enabled"))
    if "sort_order" in d:
        try:
            rule.sort_order = max(0, int(d.get("sort_order")))
        except (TypeError, ValueError):
            raise ValueError("排序要填数字")
    account_ids = None
    if "account_ids" in d:
        ids = [int(x) for x in (d.get("account_ids") or []) if str(x).isdigit()]
        account_ids = list(MailPushAccount.objects.filter(pk__in=ids).values_list("id", flat=True))
    return rule, account_ids


class MailPushRuleListAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def post(self, request):
        try:
            rule, account_ids = _rule_from_request(request.data or {})
        except ValueError as e:
            return _bad(str(e))
        if "sort_order" not in (request.data or {}):
            rule.sort_order = MailPushRule.objects.count()
        rule.save()
        if account_ids is not None:
            rule.accounts.set(account_ids)
        return Response(_rule_payload(rule), status=201)


class MailPushRuleDetailAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def patch(self, request, pk: int):
        rule = MailPushRule.objects.filter(pk=pk).first()
        if not rule:
            return _bad("规则不存在", 404)
        try:
            rule, account_ids = _rule_from_request(request.data or {}, rule)
        except ValueError as e:
            return _bad(str(e))
        rule.save()
        if account_ids is not None:
            rule.accounts.set(account_ids)
        return Response(_rule_payload(rule))

    def delete(self, request, pk: int):
        deleted, _ = MailPushRule.objects.filter(pk=pk).delete()
        if not deleted:
            return _bad("规则不存在", 404)
        return Response(status=204)


class MailPushPreviewAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def post(self, request):
        d = request.data or {}
        style = d.get("style") if d.get("style") in mail_push.STYLES else MailPushRule.STYLE_SUMMARY
        rule = {
            "name": str(d.get("name") or "").strip() or "规则名称",
            "style": style,
            "senders": [x.lower() for x in mail_push.split_lines(d.get("senders"))],
            "subject_keywords": mail_push.split_lines(d.get("subject_keywords")),
        }
        ids = [int(x) for x in (d.get("account_ids") or []) if str(x).isdigit()]
        acc = MailPushAccount.objects.filter(pk__in=ids).first() if ids else MailPushAccount.objects.first()
        s = MailPushSettings.load()
        content = eng.build_message(mail_push.sample_mail(rule), acc.name if acc else "邮箱1", rule, s.summary_chars)
        return Response({"content": content})


class MailPushRecordListAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def get(self, request):
        qs = MailPushRecord.objects.select_related("account")
        status = request.query_params.get("status") or ""
        if status:
            qs = qs.filter(status=status)
        account = request.query_params.get("account") or ""
        if account.isdigit():
            qs = qs.filter(account_id=int(account))
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(sender__icontains=q) | Q(subject__icontains=q))
        rows = [
            {
                "id": r.id,
                "created_at": _iso(r.created_at),
                "account_id": r.account_id,
                "account_name": r.account.name,
                "status": r.status,
                "rule_name": r.rule_name,
                "sender": r.sender,
                "subject": r.subject,
                "attempts": r.attempts,
                "error": r.error,
            }
            for r in qs[:300]
        ]
        return Response({"results": rows})


def _request_check():
    MailPushSettings.load()
    MailPushSettings.objects.filter(pk=1).update(check_requested_at=timezone.now())


class MailPushRecordRetryAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def post(self, request, pk: int):
        n = MailPushRecord.objects.filter(pk=pk).update(status="failed", attempts=0, error="等待重新推送")
        if not n:
            return _bad("记录不存在", 404)
        _request_check()
        return Response({"ok": True})


class MailPushCheckNowAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def post(self, request):
        _request_check()
        s = MailPushSettings.load()
        if not mail_push.worker_alive(s):
            return _bad("收信服务没有在运行：请在服务器上执行 systemctl status xinhuo-mailpush 检查")
        return Response({"ok": True})


class MailPushTestPushAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def post(self, request):
        s = MailPushSettings.load()
        if not s.webhook_url:
            return _bad("请先填写并保存 Webhook 地址")
        try:
            eng.WeComSender(s.webhook_url).send_markdown(
                "**【邮件推送】测试消息**\n> 如果你在群里看到这条，说明机器人配置正确。", retries=1
            )
        except Exception as e:
            return _bad(str(e)[:300])
        return Response({"ok": True})


urlpatterns_def = [
    ("mail-push/", MailPushOverviewAPIView, "mail-push"),
    ("mail-push/settings/", MailPushSettingsAPIView, "mail-push-settings"),
    ("mail-push/accounts/", MailPushAccountListAPIView, "mail-push-accounts"),
    ("mail-push/accounts/test/", MailPushAccountTestAPIView, "mail-push-account-test"),
    ("mail-push/accounts/<int:pk>/", MailPushAccountDetailAPIView, "mail-push-account"),
    ("mail-push/rules/", MailPushRuleListAPIView, "mail-push-rules"),
    ("mail-push/rules/<int:pk>/", MailPushRuleDetailAPIView, "mail-push-rule"),
    ("mail-push/preview/", MailPushPreviewAPIView, "mail-push-preview"),
    ("mail-push/records/", MailPushRecordListAPIView, "mail-push-records"),
    ("mail-push/records/<int:pk>/retry/", MailPushRecordRetryAPIView, "mail-push-record-retry"),
    ("mail-push/check-now/", MailPushCheckNowAPIView, "mail-push-check-now"),
    ("mail-push/test-push/", MailPushTestPushAPIView, "mail-push-test-push"),
]
