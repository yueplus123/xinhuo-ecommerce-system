# 从线上把 backend/media/payment_screenshots 打成 zip 拉回本机 backend/media（覆盖同名文件）。
# 使用前请先在服务器执行 zip（见下方 Write-Host）。

param(
    [string]$ServerHost = "192.144.236.133",
    [string]$RemoteUser = "root",
    [string]$RemoteZip = "/root/payment_screenshots_only.zip"
)

$ErrorActionPreference = "Stop"
$Backend = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ZipLocal = Join-Path $Backend "payment_screenshots_only.zip"
$Media = Join-Path $Backend "media"

Write-Host @"
=== 第 1 步：在服务器 SSH 执行（打包最新截图） ===
cd "/opt/xinhuo/xinhuo-app/backend/media" && \
zip -r -q /root/payment_screenshots_only.zip payment_screenshots && ls -lh /root/payment_screenshots_only.zip

=== 第 2 步：在本机按 Enter 继续下载并解压到 media ===
"@
[void](Read-Host "服务器 zip 完成后按 Enter")

if (-not (Test-Path $Media)) {
    New-Item -ItemType Directory -Path $Media -Force | Out-Null
}

$scpFrom = "${RemoteUser}@${ServerHost}:${RemoteZip}"
Write-Host "正在 scp: $scpFrom -> $ZipLocal"
# 不用 --%，否则变量不会展开；路径含中文时用 LiteralPath 解压即可
scp $scpFrom $ZipLocal

Write-Host "正在解压到: $Media"
Expand-Archive -LiteralPath $ZipLocal -DestinationPath $Media -Force

$n = (Get-ChildItem (Join-Path $Media "payment_screenshots") -File -ErrorAction SilentlyContinue).Count
Write-Host "完成。payment_screenshots 下约 $n 个文件。"
Write-Host "（确认无误后可手动删除: $ZipLocal）"
