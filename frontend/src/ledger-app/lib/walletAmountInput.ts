/** 零宽字符等，避免 Number 解析失败变成 0 */
function stripMoneyNoise(raw: string): string {
  return raw.replace(/[\u200b-\u200d\ufeff]/g, '')
}

/** 全角数字 ０-９ → 半角 0-9，避免输入法下提交为 0 */
export function normalizeWesternDigits(raw: string): string {
  return raw.replace(/[\uFF10-\uFF19]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) - 0xff10 + 0x30))
}

/** 受控输入：仅数字与一个小数点，小数部分最多 2 位 */
export function sanitizeWalletMoneyInput(raw: string): string {
  const cleaned = stripMoneyNoise(normalizeWesternDigits(String(raw ?? ''))).replace(/[^\d.]/g, '')
  let out = ''
  let seenDot = false
  let fracDigits = 0
  for (const ch of cleaned) {
    if (ch === '.') {
      if (!seenDot) {
        seenDot = true
        out += '.'
      }
      continue
    }
    if (!seenDot) {
      out += ch
    } else if (fracDigits < 2) {
      out += ch
      fracDigits++
    }
  }
  return out
}

/** 失焦时格式化为两位小数；空或无效则清空 */
export function formatWalletMoneyOnBlur(s: string): string {
  const t = stripMoneyNoise(normalizeWesternDigits(String(s ?? ''))).trim()
  if (t === '' || t === '.') return ''
  const n = Number(t)
  if (!Number.isFinite(n) || n < 0) return ''
  return n.toFixed(2)
}

/** 提交用：非负，四舍五入到分 */
export function parseWalletMoneySubmit(s: string): number {
  const t = stripMoneyNoise(normalizeWesternDigits(String(s ?? '')))
    .trim()
    .replace(/,/g, '')
  const n = Number(t)
  if (!Number.isFinite(n) || n < 0) return 0
  return Math.round(n * 100) / 100
}
