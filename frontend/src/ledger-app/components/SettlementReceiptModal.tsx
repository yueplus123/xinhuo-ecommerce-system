import { useEffect, useMemo } from 'react'

export type LedgerReceiptLine = {
  recordAt: string
  business: string
  amount: number
  give: number
  take: number
  profit: number
}

type Props = {
  open: boolean
  onClose: () => void
  settledAt: string
  lines: LedgerReceiptLine[]
}

function num(n: number) {
  return (Number(n) || 0).toLocaleString('zh-CN', { maximumFractionDigits: 4 })
}

function buildLedgerText(settledAt: string, lines: LedgerReceiptLine[]) {
  const w = 32
  const line = (a: string, b = '') => `${a.padEnd(w)}${b}\n`
  let t = ''
  t += line('======== 记账 · 清账 ========')
  t += line('【业务记账 清账凭证】')
  t += line('--------------------------------')
  t += line('清账时间', settledAt)
  t += line('本次笔数', `${lines.length} 笔`)
  t += line('--------------------------------')
  lines.forEach((r, i) => {
    t += line(`#${i + 1}`, r.recordAt)
    t += line('  业务', r.business)
    t += line('  金额/给你/给我/利润', `${num(r.amount)} / ${num(r.give)} / ${num(r.take)} / ${num(r.profit)}`)
    t += line('')
  })
  const sa = lines.reduce((a, r) => a + r.amount, 0)
  const sg = lines.reduce((a, r) => a + r.give, 0)
  const st = lines.reduce((a, r) => a + r.take, 0)
  const sp = lines.reduce((a, r) => a + r.profit, 0)
  t += line('--------------------------------')
  t += line('合计 金额', num(sa))
  t += line('合计 给你', num(sg))
  t += line('合计 给我', num(st))
  t += line('合计 利润', num(sp))
  t += line('================================')
  t += line('感谢您的使用', '')
  return t.trimEnd()
}

export function SettlementReceiptModal({ open, onClose, settledAt, lines }: Props) {
  const plainText = useMemo(() => {
    if (!open) return ''
    return buildLedgerText(settledAt, lines)
  }, [open, settledAt, lines])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(plainText)
    } catch {
      /* ignore */
    }
  }

  if (!open) return null

  return (
    <div className="modal-root">
      <button type="button" className="modal-backdrop" aria-label="关闭" onClick={onClose} />
      <div className="modal-dialog receipt-dialog" role="dialog" aria-modal="true" aria-labelledby="receipt-title">
        <div className="receipt-paper">
          <div className="receipt-scissor">✂ — — — — — — — —</div>
          <h2 id="receipt-title" className="receipt-store">
            记账 · 清账
          </h2>
          <p className="receipt-kind">业务记账 清账凭证</p>
          <div className="receipt-dash" />
          <dl className="receipt-meta">
            <div>
              <dt>清账时间</dt>
              <dd>{settledAt}</dd>
            </div>
            <div>
              <dt>本次笔数</dt>
              <dd>{lines.length} 笔</dd>
            </div>
          </dl>
          <div className="receipt-dash" />

          <ul className="receipt-items">
            {lines.map((r, i) => (
              <li key={`${r.recordAt}-${i}`} className="receipt-item">
                <div className="receipt-item-head">
                  <span className="receipt-no">#{i + 1}</span>
                  <span className="receipt-time">{r.recordAt}</span>
                </div>
                <div className="receipt-biz">{r.business}</div>
                <div className="receipt-nums">
                  <span>金额 {num(r.amount)}</span>
                  <span>给你 {num(r.give)}</span>
                  <span>给我 {num(r.take)}</span>
                  <span className={r.profit >= 0 ? 'pos' : 'neg'}>利润 {num(r.profit)}</span>
                </div>
              </li>
            ))}
          </ul>
          <div className="receipt-dash" />
          <dl className="receipt-totals">
            <div>
              <dt>合计 金额</dt>
              <dd>{num(lines.reduce((a, r) => a + r.amount, 0))}</dd>
            </div>
            <div>
              <dt>合计 给你</dt>
              <dd>{num(lines.reduce((a, r) => a + r.give, 0))}</dd>
            </div>
            <div>
              <dt>合计 给我</dt>
              <dd>{num(lines.reduce((a, r) => a + r.take, 0))}</dd>
            </div>
            <div>
              <dt>合计 利润</dt>
              <dd className={lines.reduce((a, r) => a + r.profit, 0) >= 0 ? 'pos' : 'neg'}>
                {num(lines.reduce((a, r) => a + r.profit, 0))}
              </dd>
            </div>
          </dl>

          <div className="receipt-dash" />
          <p className="receipt-thanks">感谢您的使用</p>
          <div className="receipt-scissor">✂ — — — — — — — —</div>
        </div>

        <div className="receipt-actions">
          <button type="button" className="btn ghost sm" onClick={copy}>
            复制小票文本
          </button>
          <button type="button" className="btn primary sm" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>
    </div>
  )
}
