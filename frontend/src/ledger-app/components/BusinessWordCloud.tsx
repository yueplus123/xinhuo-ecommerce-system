type Item = { label: string; count: number }

function labelHash(s: string) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = Math.imul(31, h) + s.charCodeAt(i) | 0
  return Math.abs(h)
}

type Props = {
  items: Item[]
  /** 最多展示词条数，避免 DOM 过大 */
  maxItems?: number
}

export function BusinessWordCloud({ items, maxItems = 80 }: Props) {
  if (items.length === 0) {
    return <p className="muted">暂无业务记账数据</p>
  }

  const slice = items.slice(0, maxItems)
  const counts = slice.map((x) => x.count)
  const max = Math.max(...counts, 1)
  const min = Math.min(...counts, max)

  const fontRem = (c: number) => {
    if (max <= min) return 1.15
    const t = (c - min) / (max - min)
    return 0.72 + t * 1.35
  }

  return (
    <div className="word-cloud" aria-label="业务词云">
      {slice.map((item) => {
        const h = labelHash(item.label)
        const hue = 88 + (h % 48)
        const rot = ((h % 11) - 5) * 0.6
        const t = max <= min ? 1 : (item.count - min) / (max - min)
        return (
          <span
            key={item.label}
            className="word-cloud-item"
            style={{
              fontSize: `${fontRem(item.count)}rem`,
              color: `hsl(${hue} 70% ${Math.round(58 + t * 22)}%)`,
              transform: `rotate(${rot}deg)`,
              opacity: 0.55 + t * 0.42,
            }}
            title={`${item.label} · ${item.count} 次`}
          >
            {item.label}
          </span>
        )
      })}
    </div>
  )
}
