import type { ReactNode } from 'react'

type PanelProps = {
  label: string
  value: string
  icon: ReactNode
  tone: 'peoples' | 'message' | 'money' | 'shopping'
}

export function DashboardPanel({ label, value, icon, tone }: PanelProps) {
  return (
    <div className="ep-panel-card">
      <div className="ep-panel-card__inner">
        <div className={`ep-panel-card__icon ep-panel-card__icon--${tone}`}>{icon}</div>
        <div className="ep-panel-card__meta">
          <div className="ep-panel-card__label">{label}</div>
          <div className="ep-panel-card__value">{value}</div>
        </div>
      </div>
    </div>
  )
}

export function DashboardCard({
  title,
  hint,
  children,
}: {
  title: string
  hint?: string
  children: ReactNode
}) {
  return (
    <section className="ep-card">
      <header className="ep-card__header">
        <h2 className="ep-card__title">{title}</h2>
        {hint ? <p className="ep-card__hint">{hint}</p> : null}
      </header>
      <div className="ep-card__body">{children}</div>
    </section>
  )
}
