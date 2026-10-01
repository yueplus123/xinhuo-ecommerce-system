import { Component, type ErrorInfo, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import App from './App'
import './index.css'
import './xinhuo-theme.css'

let root: Root | null = null

class LedgerErrorBoundary extends Component<
  { children: ReactNode },
  { error: string }
> {
  state = { error: '' }

  static getDerivedStateFromError(err: Error) {
    return { error: err?.message || String(err) }
  }

  componentDidCatch(err: Error, info: ErrorInfo) {
    console.error('[ledger-app]', err, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="panel warn" style={{ padding: 16 }}>
          <p>记账模块渲染失败：{this.state.error}</p>
          <p className="muted">请强制刷新（Ctrl+F5）后重试；若仍失败请联系管理员。</p>
        </div>
      )
    }
    return this.props.children
  }
}

/** 嵌入薪火 Vue：不用 Router，避免与 Vue Router / 双 JSX 编译冲突 */
export function mountLedgerApp(el: HTMLElement) {
  if (!root) root = createRoot(el)
  // 不用 StrictMode：嵌入 keep-alive 时双调用易导致空白
  root.render(
    <LedgerErrorBoundary>
      <App embedded />
    </LedgerErrorBoundary>,
  )
}

export function unmountLedgerApp() {
  if (root) {
    root.unmount()
    root = null
  }
}
