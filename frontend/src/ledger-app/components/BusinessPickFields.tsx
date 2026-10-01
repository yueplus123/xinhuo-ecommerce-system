import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { createPortal } from 'react-dom'
import { api, type Business } from '../lib/api'

export type CatalogReloadHint = {
  selectBizId?: string
  selectOptId?: string
}

type Props = {
  businesses: Business[]
  bizId: string | null
  optId: string | null
  onBusinessClick: (businessId: string) => void
  onOptionClick: (businessId: string, optionId: string) => void
  /** 一级/二级变更后刷新目录；可指定刷新后优先选中的业务与二级 */
  onCatalogMutated: (hint?: CatalogReloadHint) => void
  setCatalogError: (msg: string | null) => void
}

/** 一级平铺；二级仅展示当前一级下的选项；行内维护增删改 */
export function BusinessPickFields({
  businesses,
  bizId,
  optId,
  onBusinessClick,
  onOptionClick,
  onCatalogMutated,
  setCatalogError,
}: Props) {
  const [newBizName, setNewBizName] = useState('')
  const [newOptLabel, setNewOptLabel] = useState('')
  const [renameKind, setRenameKind] = useState<'biz' | 'opt' | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [renameBusy, setRenameBusy] = useState(false)
  const renameInputRef = useRef<HTMLInputElement>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<'biz' | 'opt' | null>(null)
  const [deleteBusy, setDeleteBusy] = useState(false)
  const deleteBusyRef = useRef(false)
  const deletePrimaryBtnRef = useRef<HTMLButtonElement>(null)

  const current = useMemo(
    () => (bizId ? businesses.find((b) => b.id === bizId) : null) ?? null,
    [businesses, bizId],
  )

  const run = async (fn: () => Promise<void>) => {
    setCatalogError(null)
    try {
      await fn()
    } catch (e) {
      setCatalogError((e as Error).message)
    }
  }

  const addBiz = () =>
    run(async () => {
      const name = newBizName.trim()
      if (!name) return
      const b = await api.addBusiness(name)
      setNewBizName('')
      onCatalogMutated({ selectBizId: b.id, selectOptId: b.options[0]?.id })
    })

  const openRenameBiz = () => {
    if (!bizId) return
    const b = businesses.find((x) => x.id === bizId)
    if (!b) return
    setCatalogError(null)
    setDeleteConfirm(null)
    setRenameKind('biz')
    setRenameValue(b.name)
  }

  const openRenameOpt = () => {
    if (!bizId || !optId || !current) return
    const o = current.options.find((x) => x.id === optId)
    if (!o) return
    setCatalogError(null)
    setDeleteConfirm(null)
    setRenameKind('opt')
    setRenameValue(o.label)
  }

  const renameBusyRef = useRef(false)
  useEffect(() => {
    renameBusyRef.current = renameBusy
  }, [renameBusy])

  useEffect(() => {
    deleteBusyRef.current = deleteBusy
  }, [deleteBusy])

  const closeRename = useCallback(() => {
    if (renameBusyRef.current) return
    setRenameKind(null)
    setRenameValue('')
  }, [])

  useEffect(() => {
    if (!renameKind) return
    const id = window.requestAnimationFrame(() => {
      const el = renameInputRef.current
      if (el) {
        el.focus()
        el.select()
      }
    })
    return () => cancelAnimationFrame(id)
  }, [renameKind])

  useEffect(() => {
    if (!renameKind) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !renameBusyRef.current) closeRename()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [renameKind, closeRename])

  const closeDeleteConfirm = useCallback(() => {
    if (deleteBusyRef.current) return
    setDeleteConfirm(null)
  }, [])

  useEffect(() => {
    if (!deleteConfirm) return
    const id = window.requestAnimationFrame(() => {
      deletePrimaryBtnRef.current?.focus()
    })
    return () => cancelAnimationFrame(id)
  }, [deleteConfirm])

  useEffect(() => {
    if (!deleteConfirm) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !deleteBusyRef.current) closeDeleteConfirm()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [deleteConfirm, closeDeleteConfirm])

  const openDeleteBiz = () => {
    if (!bizId) return
    setCatalogError(null)
    setRenameKind(null)
    setRenameValue('')
    setDeleteConfirm('biz')
  }

  const openDeleteOpt = () => {
    if (!bizId || !optId) return
    setCatalogError(null)
    setRenameKind(null)
    setRenameValue('')
    setDeleteConfirm('opt')
  }

  const runDelete = async () => {
    if (!deleteConfirm) return
    setDeleteBusy(true)
    setCatalogError(null)
    try {
      if (deleteConfirm === 'biz' && bizId) {
        await api.deleteBusiness(bizId)
        onCatalogMutated()
      } else if (deleteConfirm === 'opt' && bizId && optId) {
        await api.deleteOption(bizId, optId)
        onCatalogMutated({ selectBizId: bizId })
      }
      setDeleteConfirm(null)
    } catch (e) {
      setCatalogError((e as Error).message)
    } finally {
      setDeleteBusy(false)
    }
  }

  const deleteMessage = useMemo(() => {
    if (deleteConfirm === 'biz' && bizId) {
      const b = businesses.find((x) => x.id === bizId)
      const name = b?.name ?? '该项'
      return `确定删除一级业务「${name}」及其全部二级选项？此操作不可恢复。`
    }
    if (deleteConfirm === 'opt' && current && optId) {
      const o = current.options.find((x) => x.id === optId)
      const label = o?.label ?? '该项'
      return `确定删除二级选项「${label}」？此操作不可恢复。`
    }
    return ''
  }, [deleteConfirm, bizId, businesses, current, optId])

  const submitRename = async (e: FormEvent) => {
    e.preventDefault()
    const trimmed = renameValue.trim()
    if (!trimmed) {
      setCatalogError(renameKind === 'biz' ? '名称不能为空' : '二级文案不能为空')
      return
    }
    if (renameKind === 'biz' && bizId) {
      setRenameBusy(true)
      setCatalogError(null)
      try {
        await api.updateBusiness(bizId, trimmed)
        onCatalogMutated({ selectBizId: bizId, selectOptId: optId ?? undefined })
        setRenameKind(null)
        setRenameValue('')
      } catch (err) {
        setCatalogError((err as Error).message)
      } finally {
        setRenameBusy(false)
      }
      return
    }
    if (renameKind === 'opt' && bizId && optId) {
      setRenameBusy(true)
      setCatalogError(null)
      try {
        await api.updateOption(bizId, optId, trimmed)
        onCatalogMutated({ selectBizId: bizId, selectOptId: optId })
        setRenameKind(null)
        setRenameValue('')
      } catch (err) {
        setCatalogError((err as Error).message)
      } finally {
        setRenameBusy(false)
      }
    }
  }

  const addOpt = () =>
    run(async () => {
      if (!bizId) return
      const label = newOptLabel.trim()
      if (!label) return
      const o = await api.addOption(bizId, label)
      setNewOptLabel('')
      onCatalogMutated({ selectBizId: bizId, selectOptId: o.id })
    })

  return (
    <>
    <div className="biz-picker">
      <div className="biz-picker-primary">
        <div className="biz-picker-heading">
          <span className="biz-picker-subtitle">一级业务</span>
          <div className="biz-picker-admin">
            <input
              type="text"
              value={newBizName}
              onChange={(e) => setNewBizName(e.target.value)}
              placeholder="新一级名称"
              aria-label="新一级业务名称"
            />
            <button type="button" className="btn sm" onClick={() => void addBiz()}>
              添加
            </button>
            <button type="button" className="btn sm" disabled={!bizId} onClick={openRenameBiz}>
              改名
            </button>
            <button
              type="button"
              className="btn sm danger ghost"
              disabled={!bizId}
              onClick={openDeleteBiz}
            >
              删除
            </button>
          </div>
        </div>
        {businesses.length === 0 ? (
          <span className="muted">暂无一级业务，请先在上方添加。</span>
        ) : (
          <div className="chip-grid">
            {businesses.map((b) => (
              <button
                key={b.id}
                type="button"
                className={b.id === bizId ? 'chip active' : 'chip'}
                onClick={() => onBusinessClick(b.id)}
              >
                {b.name}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="biz-picker-secondary">
        <div className="biz-picker-heading">
          <span className="biz-picker-subtitle">二级选项{current ? `（${current.name}）` : ''}</span>
          <div className="biz-picker-admin">
            <input
              type="text"
              value={newOptLabel}
              onChange={(e) => setNewOptLabel(e.target.value)}
              placeholder="新二级文案，如代充CHATGPT+20美金"
              aria-label="新二级选项"
              disabled={!current}
            />
            <button type="button" className="btn sm" disabled={!bizId} onClick={() => void addOpt()}>
              添加
            </button>
            <button type="button" className="btn sm" disabled={!bizId || !optId} onClick={openRenameOpt}>
              改名
            </button>
            <button
              type="button"
              className="btn sm danger ghost"
              disabled={!bizId || !optId}
              onClick={openDeleteOpt}
            >
              删除
            </button>
          </div>
        </div>
        {!current ? (
          <span className="muted">请先选择一级业务</span>
        ) : current.options.length === 0 ? (
          <span className="muted">该业务暂无二级选项，只选一级即可提交记账。</span>
        ) : (
          <div className="chip-grid">
            {current.options.map((o) => (
              <button
                key={o.id}
                type="button"
                className={o.id === optId ? 'chip active sm' : 'chip sm'}
                onClick={() => onOptionClick(current.id, o.id)}
              >
                {o.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>

    {renameKind != null &&
      createPortal(
        <div className="modal-root modal-root-portal">
          <button
            type="button"
            className="modal-backdrop"
            aria-label="关闭"
            onClick={closeRename}
            disabled={renameBusy}
          />
          <div
            className="modal-dialog panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="biz-rename-title"
          >
            <div className="modal-head">
              <h2 id="biz-rename-title">
                {renameKind === 'biz' ? '修改一级业务名称' : '修改二级选项文案'}
              </h2>
              <button type="button" className="modal-x" aria-label="关闭" onClick={closeRename} disabled={renameBusy}>
                ×
              </button>
            </div>
            <form className="modal-body form-panel" onSubmit={(e) => void submitRename(e)}>
              <div className="field">
                <label htmlFor="biz-rename-input">{renameKind === 'biz' ? '一级名称' : '二级文案'}</label>
                <input
                  ref={renameInputRef}
                  id="biz-rename-input"
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  disabled={renameBusy}
                  autoComplete="off"
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn ghost" onClick={closeRename} disabled={renameBusy}>
                  取消
                </button>
                <button type="submit" className="btn primary" disabled={renameBusy}>
                  {renameBusy ? '保存中…' : '保存'}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body,
      )}

    {deleteConfirm != null &&
      createPortal(
        <div className="modal-root modal-root-portal modal-root-confirm">
          <button
            type="button"
            className="modal-backdrop"
            aria-label="关闭"
            onClick={closeDeleteConfirm}
            disabled={deleteBusy}
          />
          <div
            className="modal-dialog panel"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-confirm-title"
            aria-describedby="delete-confirm-desc"
          >
            <div className="modal-head">
              <h2 id="delete-confirm-title">确认删除</h2>
              <button type="button" className="modal-x" aria-label="关闭" onClick={closeDeleteConfirm} disabled={deleteBusy}>
                ×
              </button>
            </div>
            <div className="modal-body form-panel">
              <p id="delete-confirm-desc" className="confirm-dialog-text">
                {deleteMessage}
              </p>
              <div className="modal-actions">
                <button type="button" className="btn ghost" onClick={closeDeleteConfirm} disabled={deleteBusy}>
                  取消
                </button>
                <button
                  ref={deletePrimaryBtnRef}
                  type="button"
                  className="btn danger"
                  disabled={deleteBusy}
                  onClick={() => void runDelete()}
                >
                  {deleteBusy ? '删除中…' : '删除'}
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </>
  )
}
