#!/bin/bash
# 新旧库 + media 全量对比（服务器 SSH 执行）
# bash /tmp/audit_db_and_media.sh

NEW="${NEW_DB:-/var/www/xinhuo/app/backend/data/backend.sqlite3}"
OLD="${OLD_DB:-/opt/xinhuo/xinhuo-app/backend/data/backend.sqlite3}"
MEDIA_NEW="${MEDIA_NEW:-/var/www/xinhuo/app/backend/media}"
MEDIA_OLD="${MEDIA_OLD:-/opt/xinhuo/xinhuo-app/backend/media}"

count() {
  sqlite3 "$1" "SELECT COUNT(*) FROM [$2];" 2>/dev/null || echo "NA"
}

TABLES=(
  "catalog_tag|match"
  "catalog_platform|match"
  "catalog_platform_platform_tags|match"
  "catalog_business|match"
  "catalog_sku|match"
  "catalog_sku_channel_tags|match"
  "catalog_quickphrase|match"
  "catalog_quickphrasetemplate|match"
  "catalog_hallblock|match"
  "catalog_paymenttutorial|match"
  "catalog_tutorialdeploytemplate|match"
  "catalog_platformaccount|match"
  "catalog_sharedappleidpage|match"
  "catalog_paymentrecord|new_ok"
  "catalog_paymentrecordimage|new_ok"
  "catalog_subscriptionplatformoption|new_ok"
  "catalog_subscriptionreminder|new_ok"
  "catalog_subscriptionreminderwecomnotify|new_ok"
  "catalog_subscriptionreminderwecomdailydigest|new_ok"
  "catalog_staffloginmeta|info"
  "auth_user|info"
)

echo "=============================================="
echo " 薪火系统 数据/media 全量体检"
echo " 当前库: $NEW"
echo " 旧库:   $OLD"
echo "=============================================="
echo ""
printf "%-40s %8s %8s %10s  %s\n" "表名" "当前" "旧库" "旧-当前" "状态"
echo "----------------------------------------------------------------------------"

issues=0

for entry in "${TABLES[@]}"; do
  IFS='|' read -r table expect <<< "$entry"
  nc=$(count "$NEW" "$table")
  oc=$(count "$OLD" "$table")
  if [[ "$nc" == "NA" || "$oc" == "NA" ]]; then
    status="表不存在"
    issues=$((issues + 1))
    diff="NA"
  else
    diff=$((oc - nc))
    case "$expect" in
      match)    [[ "$nc" -eq "$oc" ]] && status="OK" || { status="不一致"; issues=$((issues + 1)); } ;;
      new_ok)   [[ "$nc" -ge "$oc" ]] && status="OK" || { status="当前少于旧"; issues=$((issues + 1)); } ;;
      info)     [[ "$nc" -eq "$oc" ]] && status="相同" || status="数量不同(仅提示)" ;;
    esac
  fi
  printf "%-40s %8s %8s %10s  %s\n" "$table" "$nc" "$oc" "$diff" "$status"
done

echo ""
echo "--- 旧库废弃表(新程序不用) ---"
for t in catalog_link catalog_linkcategory catalog_renewalreminder; do
  oc=$(count "$OLD" "$t")
  nc=$(count "$NEW" "$t")
  if [[ "$oc" != "NA" && "$oc" -gt 0 ]]; then
    echo "  $t: 旧=$oc 当前=$nc (可忽略)"
  fi
done

echo ""
echo "--- media 目录文件数 ---"
for sub in hall payment_screenshots links/logos; do
  fn=0; fo=0
  [[ -d "$MEDIA_NEW/$sub" ]] && fn=$(find "$MEDIA_NEW/$sub" -type f 2>/dev/null | wc -l)
  [[ -d "$MEDIA_OLD/$sub" ]] && fo=$(find "$MEDIA_OLD/$sub" -type f 2>/dev/null | wc -l)
  st="OK"
  [[ "$fo" -gt "$fn" ]] && { st="旧库更多,建议rsync"; issues=$((issues + 1)); }
  printf "  %-22s 当前=%5s  旧=%5s  %s\n" "$sub/" "$fn" "$fo" "$st"
done

echo ""
echo "--- 大厅配图文件是否存在 ---"
missing_hall=0
while IFS='|' read -r id img; do
  [[ -z "$img" ]] && continue
  if [[ ! -f "$MEDIA_NEW/$img" ]]; then
    echo "  缺失 id=$id -> $img"
    missing_hall=$((missing_hall + 1))
  fi
done < <(sqlite3 -separator '|' "$NEW" \
  "SELECT id, image FROM catalog_hallblock WHERE length(trim(coalesce(image,'')))>0;")
if [[ "$missing_hall" -eq 0 ]]; then
  echo "  全部存在"
else
  issues=$((issues + 1))
  echo "  共 $missing_hall 个缺失"
fi

echo ""
echo "--- 收款截图抽样(20条) ---"
missing_pay=0
n=0
while IFS='|' read -r _ img; do
  [[ -z "$img" ]] && continue
  n=$((n + 1))
  [[ "$n" -gt 20 ]] && break
  if [[ ! -f "$MEDIA_NEW/$img" ]]; then
    echo "  缺失 -> $img"
    missing_pay=$((missing_pay + 1))
  fi
done < <(sqlite3 -separator '|' "$NEW" "
  SELECT id, screenshot FROM catalog_paymentrecord WHERE length(trim(coalesce(screenshot,'')))>0
  UNION ALL
  SELECT id, image FROM catalog_paymentrecordimage WHERE length(trim(coalesce(image,'')))>0
  LIMIT 20;")
echo "  抽样缺失: $missing_pay / 20"
[[ "$missing_pay" -gt 0 ]] && issues=$((issues + 1))

echo ""
if [[ "$issues" -eq 0 ]]; then
  echo ">>> 结论: 未发现需处理的不一致。"
else
  echo ">>> 结论: 发现 $issues 类问题，请把全文报告发回。"
fi
