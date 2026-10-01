#!/usr/bin/env bash
# 服务器清理：压缩包 + Python 缓存（默认只预览，不删除）
#
# 用法：
#   chmod +x server_cleanup.sh
#   ./server_cleanup.sh /opt/xinhuo                    # 仅列出将删除项（DRY_RUN）
#   DRY_RUN=0 ./server_cleanup.sh /opt/xinhuo          # 真删（须再设 CONFIRM）
#   DRY_RUN=0 CONFIRM=yes ./server_cleanup.sh /opt/xinhuo   # 一键执行删除
#
# 环境变量：
#   DRY_RUN=1   只打印，不删（默认）
#   DRY_RUN=0   执行删除
#   CONFIRM=yes 与 DRY_RUN=0 配合，避免误删
#   CLEAN_PY_CACHE=1  删除 __pycache__ 与 *.pyc（默认 1）
#   CLEAN_ARCHIVES=1  删除压缩包（默认 1）

set -euo pipefail

ROOT="${1:-/opt/xinhuo}"
DRY_RUN="${DRY_RUN:-1}"
CONFIRM="${CONFIRM:-}"
CLEAN_PY_CACHE="${CLEAN_PY_CACHE:-1}"
CLEAN_ARCHIVES="${CLEAN_ARCHIVES:-1}"

if [[ ! -d "$ROOT" ]]; then
  echo "错误：目录不存在: $ROOT"
  exit 1
fi

echo "=== 清理根目录: $ROOT ==="
if [[ "$DRY_RUN" == "1" ]]; then
  echo "当前为【预览模式】，不会删除任何文件。真删请执行："
  echo "  DRY_RUN=0 CONFIRM=yes $0 \"$ROOT\""
  echo
fi

# find 排除虚拟环境与常见大包目录
PRUNE_ARGS=(
  -path "*/.venv/*" -prune -o
  -path "*/venv/*" -prune -o
  -path "*/node_modules/*" -prune -o
)

delete_file() {
  local f="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[预览] 将删除: $f"
  else
    rm -f -- "$f" && echo "[已删] $f"
  fi
}

delete_dir() {
  local d="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[预览] 将删除目录: $d"
  else
    rm -rf -- "$d" && echo "[已删目录] $d"
  fi
}

# ---------- 压缩包 ----------
if [[ "$CLEAN_ARCHIVES" == "1" ]]; then
  echo "--- 扫描压缩包（zip / tar.gz / tgz / tar.bz2 / tbz2 / 7z / rar）---"
  while IFS= read -r -d '' f; do
    delete_file "$f"
  done < <(find "$ROOT" "${PRUNE_ARGS[@]}" \
    \( -type f \( \
      -iname "*.zip" -o -iname "*.tar.gz" -o -iname "*.tgz" -o \
      -iname "*.tar.bz2" -o -iname "*.tbz2" -o -iname "*.7z" -o -iname "*.rar" \
    \) \) -print0 2>/dev/null)
fi

# ---------- Python 缓存 ----------
if [[ "$CLEAN_PY_CACHE" == "1" ]]; then
  echo "--- 扫描 __pycache__ / *.pyc ---"
  while IFS= read -r -d '' d; do
    delete_dir "$d"
  done < <(find "$ROOT" "${PRUNE_ARGS[@]}" -type d -name "__pycache__" -print0 2>/dev/null)
  while IFS= read -r -d '' f; do
    delete_file "$f"
  done < <(find "$ROOT" "${PRUNE_ARGS[@]}" -type f -name "*.pyc" -print0 2>/dev/null)
fi

if [[ "$DRY_RUN" == "0" ]]; then
  if [[ "$CONFIRM" != "yes" ]]; then
    echo
    echo "未执行删除：请加上 CONFIRM=yes 再运行。"
    exit 2
  fi
  echo
  echo "=== 清理完成 ==="
else
  echo
  echo "=== 预览结束。确认无误后执行真删 ==="
fi
