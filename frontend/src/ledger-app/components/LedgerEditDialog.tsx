import { useEffect, useState, type FormEvent } from 'react'
import { api, type LedgerRow } from '../lib/api'
import { formatLedgerBusinessLine } from '../lib/ledgerDisplay'

type Props = {
  row: LedgerRow | null
  open: boolean
  onClose: () => void
  onSaved: () => void
}

export function LedgerEditDialog({ row, open, onClose, onSaved }: Props) {
  const [project, setProject] = useState('')
  const [recordAt, setRecordAt] = useState('')
  const [recordNo, setRecordNo] = useState('')
  const [amount, setAmount] = useState('')
  const [give, setGive] = useState('')
  const [take, setTake] = useState('')
  const [profit, setProfit] = useState('')
  const [employeeName, setEmployeeName] = useState('')
  const [chatName, setChatName] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !row) return
    setErr(null)
    setProject(formatLedgerBusinessLine(row))
    setRecordAt(row.recordAt)
    setRecordNo(row.recordNo || row.recordAt)
    setAmount(String(row.amount ?? 0))
    setGive(String(row.giveAmount))
    setTake(String(row.takeAmount))
    setProfit(String(row.profit))
    setEmployeeName(row.employeeName || '')
    setChatName(row.chatName || '')
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
    const biz = project.trim()
    if (!biz) {
      setErr('请填写项目名')
      return
    }
    setErr(null)
    setLoading(true)
    try {
      await api.ledgerUpdate(row.id, {
        recordAt,
        recordNo,
        businessName: biz,
        amount: Number(amount) || 0,
        giveAmount: Number(give) || 0,
        takeAmount: Number(take) || 0,
        profit: Number(profit) || 0,
        employeeName: employeeName.trim(),
        chatName: chatName.trim(),
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
      <div className="modal-dialog panel" role="dialog" aria-modal="true" aria-labelledby="ledger-edit-title">
        <div className="modal-head">
          <h2 id="ledger-edit-title">编辑记录</h2>
          <button type="button" className="modal-x" aria-label="关闭" onClick={onClose}>
            ×
          </button>
        </div>
        <form className="modal-body form-panel" onSubmit={save}>
          <p className="muted">修改仅保存在薪火系统，不会回传机器人；保存后「数据大屏」会自动更新。</p>
          {row.statusLabel === '已清账' && <p className="muted">已清账记录可编辑字段，状态不变。</p>}

          <div className="field">
            <label htmlFor="edit-project">项目</label>
            <input id="edit-project" value={project} onChange={(e) => setProject(e.target.value)} />
          </div>

          <div className="row-2">
            <div className="field">
              <label htmlFor="edit-recordAt">记录时间</label>
              <input id="edit-recordAt" value={recordAt} onChange={(e) => setRecordAt(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="edit-recordNo">时间/单号</label>
              <input id="edit-recordNo" value={recordNo} onChange={(e) => setRecordNo(e.target.value)} />
            </div>
          </div>

          <div className="row-4">
            <div className="field">
              <label htmlFor="edit-amount">金额</label>
              <input id="edit-amount" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="edit-give">给你</label>
              <input id="edit-give" inputMode="decimal" value={give} onChange={(e) => setGive(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="edit-take">给我</label>
              <input id="edit-take" inputMode="decimal" value={take} onChange={(e) => setTake(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="edit-profit">利润</label>
              <input id="edit-profit" inputMode="decimal" value={profit} onChange={(e) => setProfit(e.target.value)} />
            </div>
          </div>

          <div className="row-2">
            <div className="field">
              <label htmlFor="edit-employee">提交人</label>
              <input id="edit-employee" value={employeeName} onChange={(e) => setEmployeeName(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="edit-chat">群</label>
              <input id="edit-chat" value={chatName} onChange={(e) => setChatName(e.target.value)} />
            </div>
          </div>

          <div className="field">
            <label>状态（只读）</label>
            <input readOnly className="readonly" value={row.statusLabel} />
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
