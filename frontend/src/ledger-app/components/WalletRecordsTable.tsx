import { useCallback, useEffect, useState } from 'react'
import { WalletEditDialog } from './WalletEditDialog'
import { api, type WalletRow } from '../lib/api'

type Props = {
  refreshTrigger?: number
  onChanged?: () => void
}

export function WalletRecordsTable({ refreshTrigger = 0, onChanged }: Props) {
  const [rows, setRows] = useState<WalletRow[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [editRow, setEditRow] = useState<WalletRow | null>(null)
  const [deleteBusyId, setDeleteBusyId] = useState<string | null>(null)

  const load = useCallback(() => {
    api
      .walletList()
      .then((list) => {
        setRows([...list].reverse())
        setErr(null)
      })
      .catch((e: Error) => setErr(e.message))
  }, [])

  useEffect(() => {
    load()
  }, [load, refreshTrigger])

  const closeEdit = useCallback(() => setEditRow(null), [])

  const handleDelete = async (r: WalletRow) => {
    setErr(null)
    setDeleteBusyId(r.id)
    try {
      await api.walletDelete(r.id)
      if (editRow?.id === r.id) setEditRow(null)
      load()
      onChanged?.()
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setDeleteBusyId(null)
    }
  }

  return (
    <section className="panel mt">
      <div className="section-head">
        <h2>钱包余额记录</h2>
        <div className="section-actions">
          <button type="button" className="btn ghost sm" onClick={load}>
            刷新
          </button>
        </div>
      </div>
      {err && <p className="error">{err}</p>}
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>记录日期</th>
              <th>微信</th>
              <th>支付宝</th>
              <th>卡片</th>
              <th>小荷包</th>
              <th>总计</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="muted">
                  暂无记录
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id}>
                  <td>{r.recordAt}</td>
                  <td>{r.wechat}</td>
                  <td>{r.alipay}</td>
                  <td>{r.card}</td>
                  <td>{r.pocket}</td>
                  <td>{r.total}</td>
                  <td className="cell-actions">
                    <button type="button" className="btn sm" onClick={() => setEditRow(r)}>
                      修改
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

      <WalletEditDialog
        row={editRow}
        open={editRow != null}
        onClose={closeEdit}
        onSaved={() => {
          load()
          onChanged?.()
        }}
      />
    </section>
  )
}
