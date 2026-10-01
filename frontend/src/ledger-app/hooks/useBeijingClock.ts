import { useEffect, useState } from 'react'
import { formatBeijing } from '../lib/beijing'

/** 按间隔刷新北京时间字符串（默认每秒） */
export function useBeijingClock(intervalMs = 1000) {
  const [t, setT] = useState(() => formatBeijing())
  useEffect(() => {
    const id = window.setInterval(() => setT(formatBeijing()), intervalMs)
    return () => window.clearInterval(id)
  }, [intervalMs])
  return t
}
