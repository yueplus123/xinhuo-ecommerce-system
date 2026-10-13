// 管理后台导航清单：左侧导航栏和管理中心首页共用这一份，新增功能只改这里
export interface NavEntry {
  title: string
  desc: string
  path: string
  icon: string // @element-plus/icons-vue 的组件名
  /** 属于本入口的子页面路径前缀（用于左侧高亮），如平台工作台、SKU 编辑页属于「平台管理」 */
  children?: string[]
}
export interface NavGroup {
  name: string
  items: NavEntry[]
}

export const NAV_GROUPS: NavGroup[] = [
  {
    name: '商品与大厅',
    items: [
      { title: '平台管理', desc: '平台、业务、SKU（价格 / 话术 / 截图 / 教程）', path: '/platforms', icon: 'Goods', children: ['/skus'] },
      { title: '大厅板块管理', desc: '大厅公告、置顶、配图', path: '/hall-blocks', icon: 'Grid' }
    ]
  },
  {
    name: '页面链接与资料',
    items: [
      { title: '链接页管理', desc: '共享苹果ID / pict / fanbox / 服务监控的链接', path: '/link-pages', icon: 'Link' },
      { title: 'AAA图文远程', desc: '远程电脑图文教程链接', path: '/payment-tutorials', icon: 'Document' },
      { title: '平台账号管理', desc: '平台账号密码表', path: '/platform-accounts', icon: 'Key' }
    ]
  },
  {
    name: '资源池',
    items: [
      { title: '教程池', desc: '机器人与 SKU 共用的教程', path: '/tutorial-pool', icon: 'Reading' },
      { title: '话术池', desc: '可复用的客服话术', path: '/phrase-pool', icon: 'ChatLineSquare' },
      { title: 'SKU 快捷话术', desc: '按 SKU 查看 / 维护快捷话术', path: '/quick-phrases', icon: 'ChatDotSquare' },
      { title: '平台标签池', desc: '平台的标签选项', path: '/platform-tag-pool', icon: 'PriceTag' },
      { title: '渠道池', desc: 'SKU 的渠道标签选项', path: '/channel-tag-pool', icon: 'Share' },
      { title: '美金代付价格池', desc: '按美金区间的代付费率', path: '/usd-proxy-price-pool', icon: 'Coin' }
    ]
  },
  {
    name: '账号与数据',
    items: [
      { title: '职员账号', desc: '新增 / 停用职员，重置密码', path: '/users', icon: 'User' },
      { title: '收款记录管理', desc: '全员收款记录，可筛选 / 导出 Excel', path: '/payment-records', icon: 'Tickets' },
      { title: '订阅提醒管理', desc: '汇总查看各员工的订阅提醒', path: '/subscription-reminders', icon: 'Bell' }
    ]
  }
]

/** 当前路径属于哪个导航入口（给左侧导航高亮用）：精确匹配，或匹配入口路径 / 子页面前缀 */
export function activeNavPath(current: string): string {
  for (const g of NAV_GROUPS) {
    for (const it of g.items) {
      const prefixes = [it.path, ...(it.children || [])]
      if (prefixes.some((p) => current === p || current.startsWith(p + '/'))) return it.path
    }
  }
  return ''
}
