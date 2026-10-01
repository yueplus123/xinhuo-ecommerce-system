import { useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Shell, type LedgerTabKey } from './layout/Shell'
import { Dashboard } from './pages/Dashboard'
import { LedgerForm } from './pages/LedgerForm'
import { WalletPage } from './pages/WalletPage'

function EmbeddedApp() {
  const [tab, setTab] = useState<LedgerTabKey>('dashboard')
  return (
    <Shell embedded activeTab={tab} onTabChange={setTab}>
      {tab === 'dashboard' && <Dashboard />}
      {tab === 'ledger' && <LedgerForm />}
      {tab === 'wallet' && <WalletPage />}
    </Shell>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Dashboard />} />
        <Route path="ledger" element={<LedgerForm />} />
        <Route path="wallet" element={<WalletPage />} />
        <Route path="*" element={<Navigate to="." replace />} />
      </Route>
    </Routes>
  )
}

type Props = {
  /** 由薪火 Vue 宿主挂载时为 true */
  embedded?: boolean
}

export default function App({ embedded }: Props) {
  if (embedded) return <EmbeddedApp />
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
