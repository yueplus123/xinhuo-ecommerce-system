/**
 * 优先已上传头像；否则用本地默认图。
 * 绝不请求外网（DiceBear 等），避免开加速器时页面卡死/打不开。
 */
export function getUserAvatarUrl(
  seed?: string | number | null,
  _size = 128,
  uploadedUrl?: string | null,
  fallback?: string
): string {
  const uploaded = String(uploadedUrl || '').trim()
  if (uploaded) return uploaded
  if (fallback) return fallback
  // 无 fallback 时返回空，由调用方用本地默认图；不走外网
  void seed
  return ''
}
