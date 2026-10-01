import { useCallback, useRef, useState, type FormEvent } from 'react'
import { LedgerRecordsTable, useLedgerMeta } from '../components/LedgerRecordsTable'
import { Toast } from '../components/Toast'
import { api } from '../lib/api'
import { formatBeijing } from '../lib/beijing'

export function LedgerForm() {
  const [ledgerRefresh, setLedgerRefresh] = useState(0)
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set())
  const [project, setProject] = useState('')
  const [amount, setAmount] = useState('')
  const [give, setGive] = useState('')
  const [take, setTake] = useState('')
  const [profit, setProfit] = useState('')
  const [employeeName, setEmployeeName] = useState('')
  const [chatName, setChatName] = useState('')
  const [toast, setToast] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const meta = useLedgerMeta()
  const projectRef = useRef<HTMLInputElement>(null)

  const reload = useCallback(() => setLedgerRefresh((n) => n + 1), [])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (submitting) return
    setErr(null)
    const biz = project.trim()
    if (!biz) {
      setErr('请填写项目名')
      return
    }
    if (!employeeName.trim() || !chatName.trim()) {
      setErr('请选择提交人与群')
      return
    }
    const a = Number(amount) || 0
    const g = Number(give) || 0
    const t = Number(take) || 0
    const p = Number(profit) || 0
    if (a === 0 && g === 0 && t === 0 && p === 0) {
      setErr('金额、给你、给我、利润至少填一项')
      return
    }
    setSubmitting(true)
    try {
      const ts = formatBeijing()
      await api.ledgerCreate({
        recordAt: ts,
        recordNo: ts,
        businessName: biz,
        amount: a,
        giveAmount: g,
        takeAmount: t,
        profit: p,
        employeeName: employeeName.trim(),
        chatName: chatName.trim(),
      })
      setProject('')
      setAmount('')
      setGive('')
      setTake('')
      setProfit('')
      setToast('添加成功')
      reload()
      window.requestAnimationFrame(() => projectRef.current?.focus())
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page ledger-workspace">
      <Toast message={toast} onHide={() => setToast(null)} />
      <h1 className="page-title">记账工作区</h1>

      <div className="panel ledger-toolbar">
        <div className="ledger-search">
          <input
            type="search"
            placeholder="搜索项目 / 提交人 / 群 / 单号…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <form className="panel ledger-manual-row" onSubmit={submit}>
        <span className="manual-label">手动补记</span>
        <input
          ref={projectRef}
          className="manual-field"
          placeholder="项目"
          value={project}
          onChange={(e) => setProject(e.target.value)}
        />
        <input
          className="manual-field manual-num"
          inputMode="decimal"
          placeholder="金额"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <input
          className="manual-field manual-num"
          inputMode="decimal"
          placeholder="给你"
          value={give}
          onChange={(e) => setGive(e.target.value)}
        />
        <input
          className="manual-field manual-num"
          inputMode="decimal"
          placeholder="给我"
          value={take}
          onChange={(e) => setTake(e.target.value)}
        />
        <input
          className="manual-field manual-num"
          inputMode="decimal"
          placeholder="利润"
          value={profit}
          onChange={(e) => setProfit(e.target.value)}
        />
        <input
          className="manual-field"
          placeholder="提交人"
          list="ledger-employees"
          value={employeeName}
          onChange={(e) => setEmployeeName(e.target.value)}
        />
        <datalist id="ledger-employees">
          {meta.employees.map((name) => (
            <option key={name} value={name} />
          ))}
        </datalist>
        <input
          className="manual-field"
          placeholder="群"
          list="ledger-chats"
          value={chatName}
          onChange={(e) => setChatName(e.target.value)}
        />
        <datalist id="ledger-chats">
          {meta.chats.map((name) => (
            <option key={name} value={name} />
          ))}
        </datalist>
        <button type="submit" className="btn primary sm manual-add" disabled={submitting}>
          {submitting ? '添加中…' : '添加'}
        </button>
        {err && <p className="error manual-error">{err}</p>}
      </form>

      <LedgerRecordsTable
        refreshTrigger={ledgerRefresh}
        searchQuery={search}
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
      />
    </div>
  )
}
