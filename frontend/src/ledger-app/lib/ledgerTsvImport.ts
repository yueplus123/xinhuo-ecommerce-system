/** 从 Excel 复制的「时间 / 项目 / 金额 / 给你 / 给我 / 利润 / 已清算」制表符分隔表解析为批量导入行 */

export type LedgerBatchImportRow = {
  recordAt: string
  businessName: string
  amount: number
  giveAmount: number
  takeAmount: number
  profit: number
  settled: boolean
}

function num(v: string | undefined): number {
  if (v == null || v === '') return 0
  const n = Number(String(v).replace(/,/g, '').trim())
  return Number.isFinite(n) ? n : 0
}

export function parseLedgerTsvPaste(text: string): LedgerBatchImportRow[] {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
  const out: LedgerBatchImportRow[] = []

  for (const line of lines) {
    if (/^时间\b/.test(line) || line.startsWith('时间\t')) continue

    let parts = line.split('\t').map((x) => x.trim())
    if (parts.length < 2) {
      parts = line.split(/\s{2,}/).map((x) => x.trim()).filter(Boolean)
    }
    if (parts.length < 2) continue

    const last = parts[parts.length - 1]?.replace(/\s/g, '') ?? ''
    const settled = last === '已清算' || last.includes('已清算')
    const cells = settled ? parts.slice(0, -1) : [...parts]
    while (cells.length < 6) cells.push('')

    const recordAt = cells[0]
    const businessName = cells[1]
    if (!recordAt || !businessName) continue

    out.push({
      recordAt,
      businessName,
      amount: num(cells[2]),
      giveAmount: num(cells[3]),
      takeAmount: num(cells[4]),
      profit: num(cells[5]),
      settled,
    })
  }

  return out
}
