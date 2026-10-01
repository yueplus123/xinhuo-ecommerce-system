import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { api, type WalletRow } from '../lib/api'
import {
  formatWalletMoneyOnBlur,
  parseWalletMoneySubmit,
  sanitizeWalletMoneyInput,
} from '../lib/walletAmountInput'

type Props = {
  row: WalletRow | null
  open: boolean
  onClose: () => void
  onSaved: () => void
}

export function WalletEditDialog({ row, open, onClose, onSaved }: Props) {
  const [recordAt, setRecordAt] = useState('')
  const [wechat, setWechat] = useState('')
  const [alipay, setAlipay] = useState('')
  const [card, setCard] = useState('')
  const [pocket, setPocket] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const totalPreview = useMemo(() => {
    return (
      parseWalletMoneySubmit(wechat) +
      parseWalletMoneySubmit(alipay) +
      parseWalletMoneySubmit(card) +
      parseWalletMoneySubmit(pocket)
    )
  }, [wechat, alipay, card, pocket])

  useEffect(() => {
    if (!open || !row) return
    queueMicrotask(() => {
      setErr(null)
      setRecordAt(row.recordAt)
      const fmt = (v: unknown) => (Number.isFinite(Number(v)) ? Number(v) : 0).toFixed(2)
      setWechat(fmt(row.wechat))
      setAlipay(fmt(row.alipay))
      setCard(fmt(row.card))
      setPocket(fmt(row.pocket))
    })
  }, [open, row])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const save = async (e: FormEvent) => {
    e.preventDefault()
    if (!row) return
    setErr(null)
    setLoading(true)
    try {
      await api.walletUpdate(row.id, {
        recordAt,
        wechat: parseWalletMoneySubmit(wechat),
        alipay: parseWalletMoneySubmit(alipay),
        card: parseWalletMoneySubmit(card),
        pocket: parseWalletMoneySubmit(pocket),
      })
      onSaved()
      onClose()
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  if (!open || !row) return null

  return (
    <div className="modal-root">
      <button type="button" className="modal-backdrop" aria-label="关闭" onClick={onClose} />
      <div className="modal-dialog panel" role="dialog" aria-modal="true" aria-labelledby="wallet-edit-title">
        <div className="modal-head">
          <h2 id="wallet-edit-title">编辑钱包余额</h2>
          <button type="button" className="modal-x" aria-label="关闭" onClick={onClose}>
            ×
          </button>
        </div>
        <form className="modal-body form-panel" onSubmit={save}>
          <div className="field">
            <label htmlFor="wallet-edit-recordAt">记录日期</label>
            <input id="wallet-edit-recordAt" value={recordAt} onChange={(e) => setRecordAt(e.target.value)} />
          </div>

          <div className="row-4">
            <div className="field">
              <label htmlFor="wallet-edit-wechat">微信</label>
              <input
                id="wallet-edit-wechat"
                inputMode="decimal"
                autoComplete="off"
                value={wechat}
                onChange={(e) => setWechat(sanitizeWalletMoneyInput(e.target.value))}
                onBlur={() => setWechat(formatWalletMoneyOnBlur(wechat))}
              />
            </div>
            <div className="field">
              <label htmlFor="wallet-edit-alipay">支付宝</label>
              <input
                id="wallet-edit-alipay"
                inputMode="decimal"
                autoComplete="off"
                value={alipay}
                onChange={(e) => setAlipay(sanitizeWalletMoneyInput(e.target.value))}
                onBlur={() => setAlipay(formatWalletMoneyOnBlur(alipay))}
              />
            </div>
            <div className="field">
              <label htmlFor="wallet-edit-card">卡片</label>
              <input
                id="wallet-edit-card"
                inputMode="decimal"
                autoComplete="off"
                value={card}
                onChange={(e) => setCard(sanitizeWalletMoneyInput(e.target.value))}
                onBlur={() => setCard(formatWalletMoneyOnBlur(card))}
              />
            </div>
            <div className="field">
              <label htmlFor="wallet-edit-pocket">小荷包</label>
              <input
                id="wallet-edit-pocket"
                inputMode="decimal"
                autoComplete="off"
                value={pocket}
                onChange={(e) => setPocket(sanitizeWalletMoneyInput(e.target.value))}
                onBlur={() => setPocket(formatWalletMoneyOnBlur(pocket))}
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="wallet-edit-total">总计（保存时与服务器一致）</label>
            <input
              id="wallet-edit-total"
              readOnly
              className="readonly"
              value={(Math.round(totalPreview * 100) / 100).toFixed(2)}
            />
          </div>

          {err && <p className="error">{err}</p>}

          <div className="modal-actions">
            <button type="button" className="btn ghost" onClick={onClose}>
              取消
            </button>
            <button type="submit" className="btn primary" disabled={loading}>
              {loading ? '保存中…' : '保存'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
