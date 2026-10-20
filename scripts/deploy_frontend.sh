#!/usr/bin/env bash
# 部署职员端：从 GitHub 的 frontend-dist 分支拉取已打包好的文件，替换 frontend/dist。
# 打包由 GitHub Actions 完成（.github/workflows/build-frontend.yml），服务器不打包。
#
# 用法：bash scripts/deploy_frontend.sh
# 回退：脚本结束时会打印回退命令（旧版本备份在 frontend/dist.bak-时间戳）
set -euo pipefail

APP=/var/www/xinhuo/app
KEY=/root/.ssh/xh_deploy
REPO_SSH=git@github.com:yueplus123/xinhuo-ecommerce-system.git
TMP=$(mktemp -d /tmp/xh_dist.XXXXXX)
export GIT_SSH_COMMAND="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20"

echo "拉取打包好的职员端…"
if ! git clone -q --depth 1 -b frontend-dist "$REPO_SSH" "$TMP/dist" 2>/dev/null; then
  echo "22 端口不通，改走 443…"
  git clone -q --depth 1 -b frontend-dist "ssh://git@ssh.github.com:443/yueplus123/xinhuo-ecommerce-system.git" "$TMP/dist"
fi
rm -rf "$TMP/dist/.git"
test -f "$TMP/dist/index.html" || { echo "打包结果里没有 index.html，放弃替换"; exit 1; }
echo "打包来源提交：$(cat "$TMP/dist/BUILD_COMMIT" 2>/dev/null | cut -c1-7)"

cd "$APP/frontend"
TS=$(date +%Y%m%d-%H%M%S)
[ -d dist ] && mv dist "dist.bak-$TS"
mv "$TMP/dist" dist
chmod -R a+rX dist
rm -rf "$TMP"

# 只保留最近 3 份备份
ls -dt dist.bak-* 2>/dev/null | tail -n +4 | xargs -r rm -rf

echo "已替换。旧版本备份：$APP/frontend/dist.bak-$TS"
echo "回退命令：cd $APP/frontend && rm -rf dist && mv dist.bak-$TS dist"
