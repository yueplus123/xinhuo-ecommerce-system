import { useEffect } from 'react'
import { createPortal } from 'react-dom'

type Props = {
  message: string | null
  onHide: () => void
  duration?: number
}

/** 轻量悬浮提示，自动消失，无需点击确认 */
export function Toast({ message, onHide, duration = 1800 }: Props) {
  useEffect(() => {
    if (!message) return
    const timer = window.setTimeout(onHide, duration)
    return () => window.clearTimeout(timer)
  }, [message, onHide, duration])

  if (!message) return null

  return createPortal(
    <div className="ledger-toast" role="status" aria-live="polite">
      {message}
    </div>,
    document.body,
  )
}
