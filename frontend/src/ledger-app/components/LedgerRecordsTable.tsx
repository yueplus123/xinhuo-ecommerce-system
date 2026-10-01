import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { LedgerEditDialog } from '../components/LedgerEditDialog'
import { SettlementReceiptModal, type LedgerReceiptLine } from '../components/SettlementReceiptModal'
import { Toast } from '../components/Toast'
import { formatBeijing } from '../lib/beijing'
import { api, type LedgerMeta, type LedgerRow } from '../lib/api'
import { formatLedgerBusinessLine, isLedgerUnsettled, ledgerStatusClass } from '../lib/ledgerDisplay'
import { notifyLedgerUpdated } from '../lib/ledgerEvents'

type Props = {
  refreshTrigger?: number
  searchQuery?: string
  onSelectionChange?: (ids: Set<string>) => void
  selectedIds?: Set<string>
}

const PAGE_SIZE_OPTIONS = [20, 50, 100, 500] as const
const ALL_EMP = '__all__'

export function LedgerRecordsTable({
  refreshTrigger = 0,
  searchQuery = '',
  onSelectionChange,
  selectedIds: controlledSelected,
}: Props) {
  const [ledger, setLedger] = useState<LedgerRow[]>([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [employeeFilter, setEmployeeFilter] = useState(ALL_EMP)
  const [internalSelected, setInternalSelected] = useState<Set<string>>(() => new Set())
  const selectedIds = controlledSelected ?? internalSelected
  const setSelectedIds = useCallback(
    (next: Set<string> | ((prev: Set<string>) => Set<string>)) => {
      const resolved = typeof next === 'function' ? next(selectedIds) : next
      if (onSelectionChange) onSelectionChange(resolved)
      else setInternalSelected(resolved)
    },
    [onSelectionChange, selectedIds],
  )
  const [err, setErr] = useState<string | null>(null)
  const [bulkBusy, setBulkBusy] = useState(false)
  const [deleteBusyId, setDeleteBusyId] = useState<string | null>(null)
  const [editRow, setEditRow] = useState<LedgerRow | null>(null)
  const [receipt, setReceipt] = useState<{ settledAt: string; lines: LedgerReceiptLine[] } | null>(null)
  const selectAllRef = useRef<HTMLInputElement>(null)
  const tableScrollRef = useRef<HTMLDivElement>(null)

  const filteredLedger = useMemo(() => {
    let rows = ledger
    if (employeeFilter !== ALL_EMP) {
      rows = rows.filter((r) => (r.employeeName || '').trim() === employeeFilter)
    }
    const q = searchQuery.trim().toLowerCase()
    if (!q) return rows
    return rows.filter((r) => {
      const blob = [
        formatLedgerBusinessLine(r),
        r.amount,
        r.giveAmount,
        r.takeAmount,
        r.profit,
        r.employeeName,
        r.chatName,
        r.statusLabel,
        r.recordNo,
        r.recordAt,
      ]
        .join(' ')
        .toLowerCase()
      return blob.includes(q)
    })
  }, [ledger, searchQuery, employeeFilter])

  const employeeTabs = useMemo(() => {
    const names = new Set<string>()
    for (const r of ledger) {
      const n = (r.employeeName || '').trim()
      if (n) names.add(n)
    }
    return [ALL_EMP, ...[...names].sort((a, b) => a.localeCompare(b, 'zh-CN'))]
  }, [ledger])

  const totalPages = Math.max(1, Math.ceil(filteredLedger.length / pageSize))
  const currentPage = Math.min(Math.max(1, page), totalPages)

  const pagedLedger = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return filteredLedger.slice(start, start + pageSize)
  }, [filteredLedger, currentPage, pageSize])

  useEffect(() => {
    tableScrollRef.current?.scrollTo({ top: 0, left: 0 })
  }, [currentPage, pageSize])

  const load = useCallback(() => {
    api
      .ledgerList()
      .then((l) => {
        setLedger(l)
        setSelectedIds((prev) => {
          const next = new Set<string>()
          for (const id of prev) {
            const row = l.find((r) => r.id === id)
            if (row && isLedgerUnsettled(row)) next.add(id)
          }
          return next
        })
        setErr(null)
      })
      .catch((e: Error) => setErr(e.message))
  }, [setSelectedIds])

  useEffect(() => {
    load()
  }, [load, refreshTrigger])

  useEffect(() => {
    setPage(1)
  }, [searchQuery, employeeFilter])

  const unsettledRows = useMemo(() => filteredLedger.filter(isLedgerUnsettled), [filteredLedger])

  const allUnsettledSelected =
    unsettledRows.length > 0 && unsettledRows.every((r) => selectedIds.has(r.id))
  const someUnsettledSelected = unsettledRows.some((r) => selectedIds.has(r.id))

  useEffect(() => {
    const el = selectAllRef.current
    if (!el) return
    el.indeterminate = someUnsettledSelected && !allUnsettledSelected
  }, [someUnsettledSelected, allUnsettledSelected])

  const toggleSelectAll = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      const ids = unsettledRows.map((r) => r.id)
      if (ids.length === 0) return new Set()
      if (ids.every((id) => prev.has(id))) {
        for (const id of ids) next.delete(id)
      } else {
        for (const id of ids) next.add(id)
      }
      return next
    })
  }

  const toggleRow = (id: string) => {
    const row = ledger.find((r) => r.id === id)
    if (!row || !isLedgerUnsettled(row)) return
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectedIdList = useMemo(() => [...selectedIds], [selectedIds])

  const bulkSetStatus = async (status: LedgerRow['status']) => {
    if (selectedIdList.length === 0) return
    setErr(null)
    setBulkBusy(true)
    try {
      await api.ledgerBulkStatus(selectedIdList, status)
      if (status === 'PROCESSED') {
        const ts = formatBeijing()
        const snapshot = selectedIdList
          .map((id) => ledger.find((r) => r.id === id))
          .filter((r): r is LedgerRow => !!r)
        setReceipt({
          settledAt: ts,
          lines: snapshot.map((r) => ({
            recordAt: r.recordAt,
            business: formatLedgerBusinessLine(r),
            amount: Number(r.amount) || 0,
            give: Number(r.giveAmount) || 0,
            take: Number(r.takeAmount) || 0,
            profit: Number(r.profit) || 0,
          })),
        })
      }
      setSelectedIds(new Set())
      load()
      notifyLedgerUpdated()
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBulkBusy(false)
    }
  }

  const unsettledSums = useMemo(() => {
    let amount = 0
    let give = 0
    let take = 0
    let profit = 0
    for (const r of filteredLedger) {
      if (!isLedgerUnsettled(r)) continue
      amount += Number(r.amount) || 0
      give += Number(r.giveAmount) || 0
      take += Number(r.takeAmount) || 0
      profit += Number(r.profit) || 0
    }
    return { amount, give, take, profit }
  }, [filteredLedger])

  const closeEdit = useCallback(() => setEditRow(null), [])

  const afterMutation = useCallback(() => {
    load()
    notifyLedgerUpdated()
  }, [load])

  const handleDelete = async (r: LedgerRow) => {
    if (!window.confirm(`确定删除「${formatLedgerBusinessLine(r)}」这条记录？`)) return
    setErr(null)
    setDeleteBusyId(r.id)
    try {
      await api.ledgerDelete(r.id)
      if (editRow?.id === r.id) setEditRow(null)
      setSelectedIds((prev) => {
        if (!prev.has(r.id)) return prev
        const next = new Set(prev)
        next.delete(r.id)
        return next
      })
      afterMutation()
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setDeleteBusyId(null)
    }
  }

  const bulkEligible = selectedIdList.length > 0

  return (
    <section className="panel mt ledger-records-panel">
      {err && <p className="error">{err}</p>}
      <div className="ledger-emp-tabs" role="tablist" aria-label="按员工分页">
        {employeeTabs.map((name) => {
          const label = name === ALL_EMP ? '全部员工' : name
          const active = employeeFilter === name
          return (
            <button
              key={name}
              type="button"
              role="tab"
              aria-selected={active}
              className={`ledger-emp-tab${active ? ' is-active' : ''}`}
              onClick={() => setEmployeeFilter(name)}
            >
              {label}
            </button>
          )
        })}
      </div>
      <div className="table-scroll" ref={tableScrollRef}>
        <table className="data-table ledger-bot-table">
          <thead>
            <tr className="sum-row">
              <th className="cell-check" aria-hidden />
              <th className="sum-row-label" colSpan={2}>
                未清账合计
              </th>
              <th className="sum-num">{unsettledSums.amount}</th>
              <th className="sum-num">{unsettledSums.give}</th>
              <th className="sum-num">{unsettledSums.take}</th>
              <th className={`sum-num ${unsettledSums.profit >= 0 ? 'pos' : 'neg'}`}>{unsettledSums.profit}</th>
              <th colSpan={4} aria-hidden />
            </tr>
            <tr>
              <th className="cell-check">
                <input
                  ref={selectAllRef}
                  type="checkbox"
                  checked={allUnsettledSelected}
                  onChange={toggleSelectAll}
                  disabled={unsettledRows.length === 0}
                  aria-label="全选待清账"
                />
              </th>
              <th>提交人</th>
              <th>项目</th>
              <th>金额</th>
              <th>给你</th>
              <th>给我</th>
              <th>利润</th>
              <th>群</th>
              <th>状态</th>
              <th>时间/单号</th>
              <th className="cell-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredLedger.length === 0 ? (
              <tr>
                <td colSpan={11} className="muted">
                  暂无
                </td>
              </tr>
            ) : (
              pagedLedger.map((r) => (
                <tr
                  key={r.id}
                  className={selectedIds.has(r.id) ? 'row-selected' : undefined}
                  onClick={() => toggleRow(r.id)}
                >
                  <td className="cell-check" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(r.id)}
                      disabled={!isLedgerUnsettled(r)}
                      onChange={() => toggleRow(r.id)}
                      aria-label={`选择 ${formatLedgerBusinessLine(r)}`}
                    />
                  </td>
                  <td>{r.employeeName || '—'}</td>
                  <td className="ellipsis" title={formatLedgerBusinessLine(r)}>
                    {formatLedgerBusinessLine(r)}
                  </td>
                  <td>{r.amount ?? 0}</td>
                  <td>{r.giveAmount}</td>
                  <td>{r.takeAmount}</td>
                  <td className={r.profit >= 0 ? 'pos' : 'neg'}>{r.profit}</td>
                  <td className="ellipsis" title={r.chatName}>
                    {r.chatName || '—'}
                  </td>
                  <td>
                    <span className={`ledger-status ${ledgerStatusClass(r)}`}>{r.statusLabel}</span>
                  </td>
                  <td>{r.recordNo || r.recordAt}</td>
                  <td className="cell-actions" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className="btn sm"
                      onClick={() => setEditRow(r)}
                    >
                      编辑
                    </button>
                    <button
                      type="button"
                      className="btn sm danger ghost"
                      disabled={deleteBusyId === r.id}
                      onClick={() => void handleDelete(r)}
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {filteredLedger.length > 0 && (
        <div className="table-pager">
          <span className="muted table-pager-meta">
            共 {filteredLedger.length} 条 · 第 {currentPage} / {totalPages} 页
          </span>
          <label className="table-pager-size">
            <span className="muted">每页</span>
            <select
              className="input-select"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value) || 50)
                setPage(1)
              }}
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
            <span className="muted">条</span>
          </label>
          <div className="table-pager-btns">
            <button type="button" className="btn ghost sm" disabled={currentPage <= 1} onClick={() => setPage(1)}>
              首页
            </button>
            <button
              type="button"
              className="btn ghost sm"
              disabled={currentPage <= 1}
              onClick={() => setPage(Math.max(1, currentPage - 1))}
            >
              上一页
            </button>
            <button
              type="button"
              className="btn ghost sm"
              disabled={currentPage >= totalPages}
              onClick={() => setPage(Math.min(totalPages, currentPage + 1))}
            >
              下一页
            </button>
            <button
              type="button"
              className="btn ghost sm"
              disabled={currentPage >= totalPages}
              onClick={() => setPage(totalPages)}
            >
              末页
            </button>
          </div>
        </div>
      )}

      <div className="ledger-table-actions">
        <button
          type="button"
          className="btn ghost sm"
          disabled={!bulkEligible || bulkBusy}
          onClick={() => void bulkSetStatus('REVERSED')}
        >
          撤销选中
        </button>
        <button
          type="button"
          className="btn primary sm"
          disabled={!bulkEligible || bulkBusy}
          onClick={() => void bulkSetStatus('PROCESSED')}
        >
          标记已处理
        </button>
        <button
          type="button"
          className="btn ghost sm"
          disabled={!bulkEligible || bulkBusy}
          onClick={() => void bulkSetStatus('ACTIVE')}
        >
          恢复有效
        </button>
        <button
          type="button"
          className="btn ghost sm"
          disabled={selectedIdList.length !== 1}
          onClick={() => {
            const id = selectedIdList[0]
            const row = ledger.find((r) => r.id === id)
            if (row) setEditRow(row)
          }}
        >
          编辑记录
        </button>
        <button
          type="button"
          className="btn danger ghost sm"
          disabled={!bulkEligible || bulkBusy}
          onClick={() => {
            const targets = selectedIdList
              .map((id) => ledger.find((r) => r.id === id))
              .filter((r): r is LedgerRow => !!r)
            if (targets.length === 0) return
            if (!window.confirm(`确定删除选中的 ${targets.length} 条记录？`)) return
            setBulkBusy(true)
            Promise.all(targets.map((r) => api.ledgerDelete(r.id)))
              .then(() => {
                setSelectedIds(new Set())
                afterMutation()
              })
              .catch((e: Error) => setErr(e.message))
              .finally(() => setBulkBusy(false))
          }}
        >
          删除选中
        </button>
        <button type="button" className="btn ghost sm" onClick={load}>
          刷新
        </button>
      </div>

      <LedgerEditDialog row={editRow} open={editRow != null} onClose={closeEdit} onSaved={afterMutation} />

      <SettlementReceiptModal
        open={receipt != null}
        onClose={() => setReceipt(null)}
        settledAt={receipt?.settledAt ?? ''}
        lines={receipt?.lines ?? []}
      />
    </section>
  )
}

export function useLedgerMeta() {
  const [meta, setMeta] = useState<LedgerMeta>({ employees: [], chats: [] })
  useEffect(() => {
    api.ledgerMeta().then(setMeta).catch(() => {})
  }, [])
  return meta
}
