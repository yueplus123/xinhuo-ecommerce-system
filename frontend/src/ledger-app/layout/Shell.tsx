import { useEffect, useState, type ReactNode } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useBeijingClock } from '../hooks/useBeijingClock'
import { isEmbedded } from '../lib/embed'

export type LedgerTabKey = 'dashboard' | 'ledger' | 'wallet'

const nav = [
  { to: '/', label: '数据大屏', icon: '📊', end: true },
  { to: '/ledger', label: '记账填写', icon: '📝' },
  { to: '/wallet', label: '钱包余额', icon: '👛' },
]

const embedTabs: { key: LedgerTabKey; label: string; icon: string }[] = [
  { key: 'dashboard', label: '数据大屏', icon: '📊' },
  { key: 'ledger', label: '记账填写', icon: '📝' },
  { key: 'wallet', label: '钱包余额', icon: '👛' },
]

const NAV_BREAKPOINT = 900

type ShellProps = {
  embedded?: boolean
  activeTab?: LedgerTabKey
  onTabChange?: (key: LedgerTabKey) => void
  children?: ReactNode
}

export function Shell({
  embedded: embeddedProp,
  activeTab = 'dashboard',
  onTabChange,
  children,
}: ShellProps) {
  const embedded = embeddedProp ?? isEmbedded()
  const clock = useBeijingClock(1000)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    const onPop = () => setSidebarOpen(false)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  useEffect(() => {
    const mq = window.matchMedia(`(min-width: ${NAV_BREAKPOINT}px)`)
    const onChange = () => {
      if (mq.matches) setSidebarOpen(false)
    }
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  useEffect(() => {
    if (!sidebarOpen) return
    const narrow = window.matchMedia('(max-width: 899px)')
    if (!narrow.matches) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [sidebarOpen])

  const closeSidebar = () => setSidebarOpen(false)
  const toggleSidebar = () => setSidebarOpen((v) => !v)

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? 'sidenav-link active' : 'sidenav-link'

  if (embedded) {
    return (
      <div className="shell shell--embed">
        <nav className="embed-tabs" aria-label="记账功能">
          {embedTabs.map((n) => (
            <button
              key={n.key}
              type="button"
              className={activeTab === n.key ? 'embed-tab active' : 'embed-tab'}
              onClick={() => onTabChange?.(n.key)}
            >
              <span className="embed-tab-icon" aria-hidden>
                {n.icon}
              </span>
              {n.label}
            </button>
          ))}
        </nav>
        <main className="main embed-main">{children}</main>
      </div>
    )
  }

  return (
    <div className={`shell ${sidebarOpen ? 'shell-drawer-open' : ''}`}>
      <button
        type="button"
        className="sidebar-backdrop"
        aria-label="关闭菜单"
        tabIndex={-1}
        onClick={closeSidebar}
      />

      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`} aria-label="主导航">
        <div className="sidebar-top">
          <div className="brand">薪火 · 记账</div>
          <button type="button" className="sidebar-close" aria-label="关闭" onClick={closeSidebar}>
            ×
          </button>
        </div>

        <nav className="sidenav">
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={navLinkClass} onClick={closeSidebar}>
              <span className="nav-icon" aria-hidden>
                {n.icon}
              </span>
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="clock" title="北京时间">
            <span className="clock-label">北京时间</span>
            <span className="clock-val">{clock}</span>
          </div>
        </div>
      </aside>

      <div className="shell-body">
        <header className="mobile-topbar">
          <button
            type="button"
            className="menu-btn"
            aria-label="打开菜单"
            aria-expanded={sidebarOpen}
            onClick={toggleSidebar}
          >
            <span className="menu-icon" aria-hidden />
          </button>
          <span className="mobile-title">薪火 · 记账</span>
        </header>

        <main className="main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
