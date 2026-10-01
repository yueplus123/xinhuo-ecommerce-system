#!/usr/bin/env bash
# 用于 cron：Gunicorn 挂掉时 Django 无法发信，由脚本探测 /health/ 并告警。
# 用法示例（crontab -e）：
#   */2 * * * * HEALTHCHECK_URL=http://127.0.0.1:8000/health/ ALERT_EMAIL=你的邮箱@qq.com /path/to/healthcheck_cron.sh
#
# 发信方式 1：系统已配置 mail/sendmail，并安装 mailx：
#   取消下面 mail 一行的注释。
# 发信方式 2：无 mail，可把失败写入日志由其它工具拉取：
#   echo "$(date -Iseconds) FAIL $HEALTHCHECK_URL" >> /var/log/xinhuo-health.log

set -euo pipefail
URL="${HEALTHCHECK_URL:-http://127.0.0.1:8000/health/}"
ALERT_EMAIL="${ALERT_EMAIL:-}"

if curl -sf --max-time 8 "$URL" | grep -q '^ok'; then
  exit 0
fi

MSG="[薪火] 探活失败: ${URL} 时间: $(date -Iseconds 2>/dev/null || date)"
echo "$MSG" >&2

if [[ -n "$ALERT_EMAIL" ]] && command -v mail >/dev/null 2>&1; then
  echo "$MSG" | mail -s "[薪火] 站点无响应/health 异常" "$ALERT_EMAIL" || true
fi

exit 1
