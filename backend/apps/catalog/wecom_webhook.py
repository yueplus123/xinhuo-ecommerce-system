"""企业微信内部群「消息推送」Webhook（原群机器人）。"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class WecomWebhookError(Exception):
    """调用失败：网络错误或返回 errcode != 0。"""

    def __init__(self, message: str, *, payload: dict | None = None):
        super().__init__(message)
        self.payload = payload or {}


def _ssl_context() -> ssl.SSLContext:
    """构建 SSL 上下文：优先使用 certifi 根证书；可选跳过校验（仅排障）。"""
    if os.environ.get("WECOM_WEBHOOK_INSECURE_SSL", "").strip().lower() in ("1", "true", "yes", "on"):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    ca_bundle = os.environ.get("WECOM_WEBHOOK_CA_BUNDLE", "").strip()
    if ca_bundle and Path(ca_bundle).is_file():
        return ssl.create_default_context(cafile=ca_bundle)
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _urlopen(req: urllib.request.Request, *, timeout: int):
    """发起 HTTPS 请求；可选绕过系统代理（公司代理常导致 SSL EOF）。"""
    ctx = _ssl_context()
    no_proxy = os.environ.get("WECOM_WEBHOOK_NO_PROXY", "").strip().lower() in ("1", "true", "yes", "on")
    if no_proxy:
        https_handler = urllib.request.HTTPSHandler(context=ctx)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), https_handler)
        return opener.open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def post_webhook_json(webhook_url: str, body: dict[str, Any], *, timeout: int = 20) -> dict[str, Any]:
    """向 Webhook 地址 POST JSON，返回解析后的响应 dict。"""
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=raw,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with _urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        try:
            text = e.read().decode("utf-8")
        except Exception:
            text = str(e)
        raise WecomWebhookError(f"HTTP {e.code}: {text}") from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        hint = ""
        if "SSL" in str(reason) or "EOF" in str(reason):
            hint = (
                " 可在项目根目录 .env 中设置 WECOM_WEBHOOK_NO_PROXY=1 绕过系统代理重试；"
                "仍失败可检查 VPN/杀毒 HTTPS 扫描，或临时 WECOM_WEBHOOK_INSECURE_SSL=1 仅作排障（勿长期开启）。"
            )
        raise WecomWebhookError(f"网络错误: {reason}{hint}") from e

    try:
        data = json.loads(text) if text else {}
    except json.JSONDecodeError as e:
        raise WecomWebhookError(f"响应非 JSON: {text[:500]}") from e

    errcode = data.get("errcode")
    if errcode is not None and int(errcode) != 0:
        raise WecomWebhookError(
            data.get("errmsg") or f"errcode={errcode}",
            payload=data,
        )
    return data


def send_markdown(webhook_url: str, content: str, *, timeout: int = 20) -> dict[str, Any]:
    """发送 markdown 类型消息（content 须为 UTF-8，官方上限约 4096 字节）。"""
    return post_webhook_json(
        webhook_url,
        {"msgtype": "markdown", "markdown": {"content": content}},
        timeout=timeout,
    )
