<script setup lang="ts">
// 邮件推送：QQ 邮箱里符合规则的新邮件 → 企业微信群。
// 收信由服务器上的 xinhuo-mailpush 服务（manage.py run_mail_push）完成，这里只管设置；改完下一轮自动生效。
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ContentWrap from '@/components/ContentWrap.vue'
import {
  createMailAccount,
  createMailRule,
  deleteMailAccount,
  deleteMailRule,
  getMailPush,
  listMailRecords,
  mailCheckNow,
  mailTestPush,
  previewMailRule,
  retryMailRecord,
  saveMailPushSettings,
  testMailAccount,
  updateMailAccount,
  updateMailRule,
  type MailPushAccount,
  type MailPushOverview,
  type MailPushRecord,
  type MailPushRule,
  type MailPushStatus,
  type MailPushStyle
} from '@/api/modules/mailPush'
import { formatDateTime, formatDateTimeSeconds, formatRequestError } from '@/utils/format'

defineOptions({ name: 'ManageMailPush' })

const STATUS: Record<MailPushStatus, { label: string; type: 'success' | 'primary' | 'info' | 'warning' | 'danger' }> = {
  pushed: { label: '已推送', type: 'success' },
  dry_run: { label: '会推送', type: 'primary' },
  ignored: { label: '未命中', type: 'info' },
  excluded: { label: '已排除', type: 'warning' },
  failed: { label: '失败', type: 'danger' }
}
const STYLE_NAME: Record<MailPushStyle, string> = { summary: '标题+摘要', code: '只推验证码', title_only: '只推标题' }

const ov = ref<MailPushOverview | null>(null)
const loadErr = ref('')
const tab = ref('overview')
const sum = (o: Partial<Record<string, number>> = {}) => Object.values(o).reduce((a, b) => a + (b || 0), 0)
const live = computed(() => !!ov.value && !ov.value.settings.dry_run)

async function load() {
  try {
    const { data } = await getMailPush()
    ov.value = data
    loadErr.value = ''
  } catch (e) {
    loadErr.value = formatRequestError(e, '加载失败')
  }
}

let timer: number | undefined
onMounted(() => {
  load()
  timer = window.setInterval(() => !document.hidden && load(), 10000)
})
onBeforeUnmount(() => window.clearInterval(timer))

// ---------------- 顶部：模式 / 立即检查 ----------------
const modeSaving = ref(false)
async function toggleMode(toLive: boolean) {
  if (!ov.value) return
  if (toLive) {
    if (!ov.value.settings.has_webhook) {
      ElMessage.warning('请先在「推送设置」里填写 Webhook 地址')
      tab.value = 'settings'
      return
    }
    try {
      await ElMessageBox.confirm('切换为正式推送后，命中规则的新邮件会真的发到企业微信群。确定吗？', '开启正式推送', {
        type: 'warning'
      })
    } catch {
      return
    }
  }
  modeSaving.value = true
  try {
    const { data } = await saveMailPushSettings({ dry_run: !toLive })
    ov.value = data
    ElMessage.success(toLive ? '已开启正式推送' : '已切换为观察模式')
  } catch (e) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    modeSaving.value = false
  }
}

async function checkNow() {
  try {
    await mailCheckNow()
    ElMessage.success('已通知收信服务，几秒后刷新结果')
    window.setTimeout(load, 6000)
  } catch (e) {
    ElMessage.error(formatRequestError(e, '操作失败'))
  }
}

function accountState(a: MailPushAccount) {
  if (!a.enabled) return { label: '已停用', type: 'info' as const }
  if (a.last_ok === null) return { label: '等待检查', type: 'info' as const }
  return a.last_ok ? { label: '正常', type: 'success' as const } : { label: '检查失败', type: 'danger' as const }
}

const setupSteps = computed(() => {
  const o = ov.value
  if (!o) return []
  return [
    { done: o.settings.has_webhook, text: '填写企业微信群机器人 Webhook 地址', to: 'settings' },
    { done: o.accounts.length > 0, text: '添加 QQ 邮箱', to: 'accounts' },
    { done: o.rules.length > 0, text: '新建推送规则（只推特定发件人或标题）', to: 'rules' },
    { done: !o.settings.dry_run, text: '观察几天，规则调准后切换为正式推送', to: '' }
  ]
})
const setupDone = computed(() => setupSteps.value.slice(0, 3).every((s) => s.done))

// ---------------- 邮箱 ----------------
const accDlg = reactive({ show: false, id: null as number | null, name: '', email: '', auth_code: '', msg: '', ok: false, busy: false })
function editAccount(a: MailPushAccount | null) {
  Object.assign(accDlg, {
    show: true,
    id: a?.id ?? null,
    name: a?.name ?? `邮箱${(ov.value?.accounts.length || 0) + 1}`,
    email: a?.email ?? '',
    auth_code: '',
    msg: '',
    ok: false
  })
}
async function testAccount() {
  accDlg.busy = true
  accDlg.msg = '正在连接 QQ 邮箱…'
  accDlg.ok = true
  try {
    const { data } = await testMailAccount({ id: accDlg.id, email: accDlg.email, auth_code: accDlg.auth_code })
    accDlg.msg = data.detail
  } catch (e) {
    accDlg.msg = formatRequestError(e, '登录失败')
    accDlg.ok = false
  } finally {
    accDlg.busy = false
  }
}
async function saveAccount() {
  accDlg.busy = true
  try {
    const body = { name: accDlg.name, email: accDlg.email, auth_code: accDlg.auth_code }
    if (accDlg.id) await updateMailAccount(accDlg.id, body)
    else await createMailAccount(body)
    accDlg.show = false
    ElMessage.success('已保存，下一轮检查开始监控（第一次只记住位置，不推历史邮件）')
    await load()
  } catch (e) {
    accDlg.msg = formatRequestError(e, '保存失败')
    accDlg.ok = false
  } finally {
    accDlg.busy = false
  }
}
async function removeAccount() {
  if (!accDlg.id) return
  try {
    await ElMessageBox.confirm('删除后这个邮箱的推送记录也会删除（不影响邮箱里的邮件）。确定吗？', '删除邮箱', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteMailAccount(accDlg.id)
    accDlg.show = false
    await load()
  } catch (e) {
    ElMessage.error(formatRequestError(e, '删除失败'))
  }
}
async function toggleAccount(a: MailPushAccount, enabled: boolean) {
  try {
    await updateMailAccount(a.id, { enabled })
    await load()
  } catch (e) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  }
}

// ---------------- 规则 ----------------
const ruleDlg = reactive({
  show: false,
  id: null as number | null,
  name: '',
  senders: '',
  subject_keywords: '',
  style: 'summary' as MailPushStyle,
  account_ids: [] as number[],
  err: '',
  busy: false,
  preview: ''
})
function editRule(r: MailPushRule | null, prefill: Partial<typeof ruleDlg> = {}) {
  Object.assign(ruleDlg, {
    show: true,
    id: r?.id ?? null,
    name: r?.name ?? '',
    senders: r?.senders.join('，') ?? '',
    subject_keywords: r?.subject_keywords.join('，') ?? '',
    style: r?.style ?? 'summary',
    account_ids: r ? [...r.account_ids] : [],
    err: '',
    preview: '',
    ...prefill
  })
  runPreview()
}
const ruleBody = () => ({
  name: ruleDlg.name,
  senders: ruleDlg.senders,
  subject_keywords: ruleDlg.subject_keywords,
  style: ruleDlg.style,
  account_ids: ruleDlg.account_ids
})
let pvTimer: number | undefined
function runPreview() {
  window.clearTimeout(pvTimer)
  pvTimer = window.setTimeout(async () => {
    try {
      const { data } = await previewMailRule(ruleBody())
      ruleDlg.preview = data.content
    } catch {
      /* 预览失败不提示 */
    }
  }, 250)
}
async function saveRule() {
  ruleDlg.busy = true
  try {
    if (ruleDlg.id) await updateMailRule(ruleDlg.id, ruleBody())
    else await createMailRule(ruleBody())
    ruleDlg.show = false
    ElMessage.success('规则已保存，对之后收到的邮件生效')
    await load()
  } catch (e) {
    ruleDlg.err = formatRequestError(e, '保存失败')
  } finally {
    ruleDlg.busy = false
  }
}
async function removeRule() {
  if (!ruleDlg.id) return
  try {
    await ElMessageBox.confirm(`确定删除规则「${ruleDlg.name}」吗？`, '删除规则', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteMailRule(ruleDlg.id)
    ruleDlg.show = false
    await load()
  } catch (e) {
    ElMessage.error(formatRequestError(e, '删除失败'))
  }
}
async function toggleRule(r: MailPushRule, enabled: boolean) {
  try {
    await updateMailRule(r.id, { enabled })
    await load()
  } catch (e) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  }
}

// 群消息预览：把企微 markdown（**粗体**、<font>、> 引用）拆成片段渲染，不用 v-html
type Seg = { t: string; b?: boolean; w?: boolean }
const FONT_RE = /<font color="\w+">(.*?)<\/font>/
function parseLine(line: string): Seg[] {
  const out: Seg[] = []
  const re = /\*\*(.+?)\*\*|<font color="\w+">(.*?)<\/font>/g
  let last = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(line))) {
    if (m.index > last) out.push({ t: line.slice(last, m.index) })
    if (m[1] !== undefined) {
      const fm = FONT_RE.exec(m[1])
      if (fm) {
        out.push({ t: m[1].slice(0, fm.index), b: true }, { t: fm[1], b: true, w: true })
        out.push({ t: m[1].slice(fm.index + fm[0].length), b: true })
      } else out.push({ t: m[1], b: true })
    } else out.push({ t: m[2], w: true })
    last = re.lastIndex
  }
  if (last < line.length) out.push({ t: line.slice(last) })
  return out
}
const previewLines = computed(() =>
  ruleDlg.preview.split('\n').map((l) => ({ quote: l.startsWith('> '), segs: parseLine(l.startsWith('> ') ? l.slice(2) : l) }))
)

// 排除规则
const exDlg = reactive({ show: false, senders: '', keywords: '', busy: false })
function editExclude() {
  if (!ov.value) return
  Object.assign(exDlg, {
    show: true,
    senders: ov.value.settings.exclude_senders.join('\n'),
    keywords: ov.value.settings.exclude_keywords.join('\n')
  })
}
async function saveExclude() {
  exDlg.busy = true
  try {
    const { data } = await saveMailPushSettings({ exclude_senders: exDlg.senders, exclude_keywords: exDlg.keywords })
    ov.value = data
    exDlg.show = false
    ElMessage.success('排除规则已保存')
  } catch (e) {
    ElMessage.error(formatRequestError(e, '保存失败'))
  } finally {
    exDlg.busy = false
  }
}

// ---------------- 记录 ----------------
const rec = reactive({ status: '', q: '', account: '', rows: [] as MailPushRecord[], loading: false })
let recTimer: number | undefined
async function loadRecords() {
  rec.loading = true
  try {
    const { data } = await listMailRecords({ status: rec.status, q: rec.q.trim(), account: rec.account })
    rec.rows = data.results
  } catch (e) {
    ElMessage.error(formatRequestError(e, '加载失败'))
  } finally {
    rec.loading = false
  }
}
function searchRecords() {
  window.clearTimeout(recTimer)
  recTimer = window.setTimeout(loadRecords, 300)
}
function onTab(name: string | number) {
  if (name === 'records') loadRecords()
  if (name === 'settings') fillSettings()
}
async function retry(r: MailPushRecord) {
  try {
    await retryMailRecord(r.id)
    ElMessage.success('已安排重新推送')
    window.setTimeout(loadRecords, 6000)
  } catch (e) {
    ElMessage.error(formatRequestError(e, '操作失败'))
  }
}
function ruleFrom(r: MailPushRecord) {
  const domain = r.sender.includes('@') ? '@' + r.sender.split('@')[1] : r.sender
  tab.value = 'rules'
  editRule(null, { name: domain.replace(/^@/, '').split('.')[0], senders: domain })
}
const statusFilters = computed(() => {
  const c = ov.value?.counts || {}
  return [
    { v: '', label: `全部 ${sum(c)}` },
    ...(Object.keys(STATUS) as MailPushStatus[]).map((k) => ({ v: k, label: `${STATUS[k].label} ${c[k] || 0}` }))
  ]
})

// ---------------- 设置 ----------------
const st = reactive({ webhook_url: '', poll_interval: 60, summary_chars: 400, busy: false })
function fillSettings() {
  if (!ov.value) return
  st.webhook_url = ov.value.settings.webhook_url
  st.poll_interval = ov.value.settings.poll_interval
  st.summary_chars = ov.value.settings.summary_chars
}
async function saveSettings(silent = false) {
  st.busy = true
  try {
    const { data } = await saveMailPushSettings({
      webhook_url: st.webhook_url,
      poll_interval: st.poll_interval,
      summary_chars: st.summary_chars
    })
    ov.value = data
    fillSettings()
    if (!silent) ElMessage.success('设置已保存')
    return true
  } catch (e) {
    ElMessage.error(formatRequestError(e, '保存失败'))
    return false
  } finally {
    st.busy = false
  }
}
async function testPush() {
  if (!(await saveSettings(true))) return
  try {
    await mailTestPush()
    ElMessage.success('测试消息已发送，去企业微信群里看看')
  } catch (e) {
    ElMessage.error(formatRequestError(e, '发送失败'))
  }
}
</script>

<template>
  <ContentWrap title="邮件推送">
    <template #header>
      <div v-if="ov" class="hdr">
        <span class="sub">
          {{ ov.settings.last_round_at ? `上次检查 ${formatDateTimeSeconds(ov.settings.last_round_at).slice(11)}` : '还没有检查过' }}
          · 每 {{ ov.settings.poll_interval }} 秒
        </span>
        <ElSwitch
          :model-value="live"
          :loading="modeSaving"
          inline-prompt
          active-text="正式推送"
          inactive-text="观察模式"
          style="--el-switch-on-color: #16a34a"
          @change="(v: string | number | boolean) => toggleMode(!!v)"
        />
        <ElButton size="small" type="primary" plain @click="checkNow">立即检查</ElButton>
      </div>
    </template>

    <ElAlert v-if="loadErr" :title="loadErr" type="error" show-icon :closable="false" class="mb" />
    <template v-if="ov">
      <ElAlert v-if="!ov.settings.worker_alive" type="error" show-icon :closable="false" class="mb">
        收信服务没有在运行，邮件不会被检查。请在服务器上执行 <code>systemctl status xinhuo-mailpush</code> 检查。
      </ElAlert>
      <ElAlert v-if="ov.settings.dry_run" type="info" show-icon :closable="false" class="mb">
        当前为<b>观察模式</b>：只记录哪些邮件"会推送"，不会真的发到企业微信群。规则调准后，打开右上角开关切换为正式推送。
      </ElAlert>

      <ElTabs v-model="tab" @tab-change="onTab">
        <!-- 总览 -->
        <ElTabPane label="总览" name="overview">
          <div v-if="!setupDone" class="setup">
            <b>开始使用</b>
            <ol>
              <li v-for="s in setupSteps" :key="s.text" :class="{ done: s.done }">
                {{ s.done ? '已完成：' : '' }}{{ s.text }}
                <ElButton v-if="!s.done && s.to" link type="primary" @click="tab = s.to">去设置</ElButton>
              </li>
            </ol>
          </div>
          <div class="stats">
            <div class="stat">
              <span class="k">今日处理</span><span class="v">{{ sum(ov.today) }}</span><span class="n">新收到并检查过的邮件</span>
            </div>
            <div class="stat">
              <span class="k">{{ live ? '今日已推送' : '今日会推送' }}</span>
              <span class="v ac">{{ (ov.today.pushed || 0) + (ov.today.dry_run || 0) }}</span>
              <span class="n">{{ live ? '已发到群里' : '观察模式下未真实发送' }}</span>
            </div>
            <div class="stat">
              <span class="k">未命中 / 已排除</span>
              <span class="v">{{ ov.today.ignored || 0 }} / {{ ov.today.excluded || 0 }}</span>
              <span class="n">去「推送记录」检查有没有漏的</span>
            </div>
            <div class="stat">
              <span class="k">推送失败</span><span class="v bad">{{ ov.today.failed || 0 }}</span><span class="n">之后几轮自动重试</span>
            </div>
          </div>
          <h3 class="sec">邮箱状态</h3>
          <ElEmpty v-if="!ov.accounts.length" description="还没有添加邮箱" :image-size="60" />
          <div class="boxes">
            <div v-for="a in ov.accounts" :key="a.id" class="box" :class="{ bad: a.enabled && a.last_ok === false }">
              <div class="row between">
                <b>{{ a.name }}</b><ElTag :type="accountState(a).type" size="small">{{ accountState(a).label }}</ElTag>
              </div>
              <span class="sub">{{ a.email }}</span>
              <span class="sub">今日处理 {{ sum(a.today) }} 封 · {{ live ? '推送' : '会推送' }} {{ (a.today.pushed || 0) + (a.today.dry_run || 0) }} 封</span>
              <span v-if="a.enabled && a.last_ok === false" class="err">{{ a.last_error }}</span>
              <span v-else-if="a.last_check_at" class="sub">上次检查 {{ formatDateTimeSeconds(a.last_check_at).slice(11) }}</span>
            </div>
          </div>
        </ElTabPane>

        <!-- 邮箱账号 -->
        <ElTabPane :label="`邮箱账号 ${ov.accounts.length}`" name="accounts">
          <div class="row between mb">
            <span class="sub">授权码只保存在服务器数据库，页面上不显示。获取：QQ 邮箱网页版 → 设置 → 账号与安全 → 开启 IMAP/SMTP 服务 → 生成授权码。</span>
            <ElButton type="primary" @click="editAccount(null)">添加邮箱</ElButton>
          </div>
          <ElTable :data="ov.accounts" border>
            <ElTableColumn label="名称" prop="name" width="140" />
            <ElTableColumn label="邮箱地址" prop="email" min-width="200" />
            <ElTableColumn label="授权码" width="100">
              <template #default="{ row }">
                <ElTag :type="row.has_auth_code ? 'success' : 'danger'" size="small">{{ row.has_auth_code ? '已填写' : '未填写' }}</ElTag>
              </template>
            </ElTableColumn>
            <ElTableColumn label="状态" min-width="220">
              <template #default="{ row }">
                <ElTag :type="accountState(row).type" size="small">{{ accountState(row).label }}</ElTag>
                <div v-if="row.enabled && row.last_ok === false" class="err">{{ row.last_error }}</div>
              </template>
            </ElTableColumn>
            <ElTableColumn label="启用" width="80" align="center">
              <template #default="{ row }">
                <ElSwitch :model-value="row.enabled" @change="(v: string | number | boolean) => toggleAccount(row, !!v)" />
              </template>
            </ElTableColumn>
            <ElTableColumn label="" width="90" align="center">
              <template #default="{ row }"><ElButton size="small" @click="editAccount(row)">编辑</ElButton></template>
            </ElTableColumn>
          </ElTable>
        </ElTabPane>

        <!-- 推送规则 -->
        <ElTabPane :label="`推送规则 ${ov.rules.length}`" name="rules">
          <div class="row between mb">
            <span class="sub">满足任意一条规则就推送；同一条规则里「发件人」和「标题关键词」都填时需同时满足。</span>
            <ElButton type="primary" @click="editRule(null)">新建规则</ElButton>
          </div>
          <ElEmpty v-if="!ov.rules.length" description="还没有规则：没有规则时所有邮件都「未命中」，不会推送" :image-size="60" />
          <div class="rules">
            <div v-for="r in ov.rules" :key="r.id" class="rule" :class="{ off: !r.enabled }">
              <div class="row between">
                <div class="row">
                  <b>{{ r.name }}</b>
                  <ElTag size="small" type="info">{{ STYLE_NAME[r.style] }}</ElTag>
                  <span class="sub">今日命中 {{ r.today_hits }} 次</span>
                </div>
                <div class="row">
                  <ElSwitch :model-value="r.enabled" @change="(v: string | number | boolean) => toggleRule(r, !!v)" />
                  <ElButton size="small" @click="editRule(r)">编辑</ElButton>
                </div>
              </div>
              <div class="line">
                <span class="lbl">发件人</span>
                <span v-for="s in r.senders" :key="s" class="chip">{{ s }}</span>
                <span v-if="!r.senders.length" class="sub">不限</span>
              </div>
              <div class="line">
                <span class="lbl">标题包含</span>
                <span v-for="s in r.subject_keywords" :key="s" class="chip kw">{{ s }}</span>
                <span v-if="!r.subject_keywords.length" class="sub">不限</span>
              </div>
              <div class="line"><span class="lbl">适用邮箱</span>{{ r.account_names.length ? r.account_names.join('、') : '全部邮箱' }}</div>
            </div>
            <div class="rule exclude">
              <div class="row between"><b>排除规则（优先级最高）</b><ElButton size="small" @click="editExclude">编辑</ElButton></div>
              <div class="line">
                <span class="lbl">发件人</span>
                <span v-for="s in ov.settings.exclude_senders" :key="s" class="chip x">{{ s }}</span>
                <span v-if="!ov.settings.exclude_senders.length" class="sub">无</span>
              </div>
              <div class="line">
                <span class="lbl">标题包含</span>
                <span v-for="s in ov.settings.exclude_keywords" :key="s" class="chip x">{{ s }}</span>
                <span v-if="!ov.settings.exclude_keywords.length" class="sub">无</span>
              </div>
            </div>
          </div>
        </ElTabPane>

        <!-- 推送记录 -->
        <ElTabPane label="推送记录" name="records">
          <div class="row mb wrap">
            <ElRadioGroup v-model="rec.status" size="small" @change="loadRecords">
              <ElRadioButton v-for="f in statusFilters" :key="f.v" :value="f.v">{{ f.label }}</ElRadioButton>
            </ElRadioGroup>
            <ElSelect v-model="rec.account" size="small" placeholder="全部邮箱" clearable style="width: 140px" @change="loadRecords">
              <ElOption v-for="a in ov.accounts" :key="a.id" :label="a.name" :value="String(a.id)" />
            </ElSelect>
            <ElInput v-model="rec.q" size="small" placeholder="搜索发件人或标题" clearable style="width: 220px" @input="searchRecords" />
            <span class="sub">只保存发件人、标题和结果，不存正文，保留 90 天</span>
          </div>
          <ElTable v-loading="rec.loading" :data="rec.rows" border empty-text="暂无记录：第一次检查只记住位置，之后的新邮件才会出现在这里">
            <ElTableColumn label="时间" width="150">
              <template #default="{ row }">{{ formatDateTime(row.created_at).slice(5) }}</template>
            </ElTableColumn>
            <ElTableColumn label="邮箱" prop="account_name" width="100" />
            <ElTableColumn label="结果" width="90">
              <template #default="{ row }">
                <ElTag :type="STATUS[row.status as MailPushStatus].type" size="small">{{ STATUS[row.status as MailPushStatus].label }}</ElTag>
              </template>
            </ElTableColumn>
            <ElTableColumn label="规则" width="130">
              <template #default="{ row }">{{ row.rule_name || '—' }}</template>
            </ElTableColumn>
            <ElTableColumn label="发件人" prop="sender" min-width="180" />
            <ElTableColumn label="标题" min-width="260">
              <template #default="{ row }">
                {{ row.subject }}
                <div v-if="row.error" class="err">{{ row.error }}</div>
              </template>
            </ElTableColumn>
            <ElTableColumn label="" width="120" align="center">
              <template #default="{ row }">
                <ElButton v-if="row.status === 'failed' || row.status === 'pushed'" size="small" @click="retry(row)">重新推送</ElButton>
                <ElButton v-else-if="row.status === 'ignored'" size="small" @click="ruleFrom(row)">按此建规则</ElButton>
              </template>
            </ElTableColumn>
          </ElTable>
        </ElTabPane>

        <!-- 推送设置 -->
        <ElTabPane label="推送设置" name="settings">
          <ElForm label-position="top" class="settings" @submit.prevent>
            <ElFormItem label="企业微信群机器人 Webhook 地址">
              <ElInput v-model="st.webhook_url" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
              <div class="sub">企业微信群聊 → 右上角 … → 消息推送（群机器人）→ 添加 → 复制 Webhook 地址。建议单独建一个「邮件通知」群。</div>
            </ElFormItem>
            <div class="row">
              <ElFormItem label="检查间隔（秒，30–3600）">
                <ElInputNumber v-model="st.poll_interval" :min="30" :max="3600" :step="10" />
              </ElFormItem>
              <ElFormItem label="摘要字数（50–1500）">
                <ElInputNumber v-model="st.summary_chars" :min="50" :max="1500" :step="50" />
              </ElFormItem>
            </div>
            <div class="row">
              <ElButton :loading="st.busy" @click="testPush">发送测试消息</ElButton>
              <ElButton type="primary" :loading="st.busy" @click="saveSettings()">保存设置</ElButton>
            </div>
          </ElForm>
        </ElTabPane>
      </ElTabs>
    </template>

    <!-- 邮箱弹窗 -->
    <ElDialog v-model="accDlg.show" :title="accDlg.id ? '编辑邮箱' : '添加邮箱'" width="480px">
      <ElForm label-position="top" @submit.prevent>
        <ElFormItem label="名称（推送时显示，比如「主邮箱」）"><ElInput v-model="accDlg.name" maxlength="30" /></ElFormItem>
        <ElFormItem label="QQ 邮箱地址"><ElInput v-model="accDlg.email" placeholder="123456@qq.com" /></ElFormItem>
        <ElFormItem label="授权码（不是 QQ 密码）">
          <ElInput
            v-model="accDlg.auth_code"
            type="password"
            show-password
            autocomplete="new-password"
            :placeholder="accDlg.id ? '已保存，不修改就留空' : '16 位授权码'"
          />
        </ElFormItem>
      </ElForm>
      <ElAlert v-if="accDlg.msg" :title="accDlg.msg" :type="accDlg.ok ? 'success' : 'error'" :closable="false" show-icon />
      <template #footer>
        <ElButton v-if="accDlg.id" type="danger" plain class="fl" @click="removeAccount">删除</ElButton>
        <ElButton :loading="accDlg.busy" @click="testAccount">测试登录</ElButton>
        <ElButton type="primary" :loading="accDlg.busy" @click="saveAccount">保存</ElButton>
      </template>
    </ElDialog>

    <!-- 规则弹窗 -->
    <ElDialog v-model="ruleDlg.show" :title="ruleDlg.id ? `编辑规则 · ${ruleDlg.name}` : '新建规则'" width="860px">
      <div class="rule-edit">
        <ElForm label-position="top" class="rule-form" @submit.prevent>
          <ElFormItem label="规则名称（推送消息里显示的分类）">
            <ElInput v-model="ruleDlg.name" maxlength="30" placeholder="例如：PayPal收款" @input="runPreview" />
          </ElFormItem>
          <ElFormItem label="发件人（@开头 = 整个域名；逗号分隔）">
            <ElInput v-model="ruleDlg.senders" placeholder="@paypal.com，boss@qq.com" @input="runPreview" />
          </ElFormItem>
          <ElFormItem label="标题包含（任意一个即可；留空 = 不限）">
            <ElInput v-model="ruleDlg.subject_keywords" placeholder="收到，付款" @input="runPreview" />
          </ElFormItem>
          <ElFormItem label="推送样式">
            <ElRadioGroup v-model="ruleDlg.style" @change="runPreview">
              <ElRadioButton v-for="(v, k) in STYLE_NAME" :key="k" :value="k">{{ v }}</ElRadioButton>
            </ElRadioGroup>
          </ElFormItem>
          <ElFormItem label="适用邮箱（不选 = 全部邮箱）">
            <ElSelect v-model="ruleDlg.account_ids" multiple placeholder="全部邮箱" style="width: 100%" @change="runPreview">
              <ElOption v-for="a in ov?.accounts || []" :key="a.id" :label="a.name" :value="a.id" />
            </ElSelect>
          </ElFormItem>
        </ElForm>
        <div class="pv">
          <div class="sub">群消息预览（示例邮件）</div>
          <div class="chat">
            <div class="bot">机器人</div>
            <div class="bubble">
              <div v-for="(l, i) in previewLines" :key="i" :class="{ q: l.quote }">
                <template v-for="(s, j) in l.segs" :key="j">
                  <b v-if="s.b" :class="{ warn: s.w }">{{ s.t }}</b>
                  <span v-else :class="{ warn: s.w }">{{ s.t }}</span>
                </template>
                <template v-if="!l.segs.length">&nbsp;</template>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="ruleDlg.err" class="err">{{ ruleDlg.err }}</div>
      <template #footer>
        <ElButton v-if="ruleDlg.id" type="danger" plain class="fl" @click="removeRule">删除</ElButton>
        <ElButton @click="ruleDlg.show = false">取消</ElButton>
        <ElButton type="primary" :loading="ruleDlg.busy" @click="saveRule">保存规则</ElButton>
      </template>
    </ElDialog>

    <!-- 排除规则弹窗 -->
    <ElDialog v-model="exDlg.show" title="排除规则" width="520px">
      <ElForm label-position="top" @submit.prevent>
        <ElFormItem label="这些发件人一律不推（一行一个，可以用 @域名）">
          <ElInput v-model="exDlg.senders" type="textarea" :rows="3" />
        </ElFormItem>
        <ElFormItem label="标题包含这些词就不推（一行一个）">
          <ElInput v-model="exDlg.keywords" type="textarea" :rows="5" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="exDlg.show = false">取消</ElButton>
        <ElButton type="primary" :loading="exDlg.busy" @click="saveExclude">保存</ElButton>
      </template>
    </ElDialog>
  </ContentWrap>
</template>

<style scoped>
.hdr {
  float: right;
  display: flex;
  align-items: center;
  gap: 12px;
}
.mb {
  margin-bottom: 12px;
}
.sec {
  margin: 20px 0 10px;
  font-size: 15px;
}
.sub {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.err {
  margin-top: 4px;
  color: var(--el-color-danger);
  font-size: 12px;
}
.row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.row.wrap {
  flex-wrap: wrap;
}
.between {
  justify-content: space-between;
}
.setup {
  margin-bottom: 16px;
  padding: 12px 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.setup ol {
  margin: 6px 0 0;
  padding-left: 20px;
  line-height: 2;
}
.setup li.done {
  color: var(--el-color-success);
}
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.stat .k {
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.stat .v {
  font-size: 26px;
  font-weight: 700;
}
.stat .v.ac {
  color: #c2410c;
}
.stat .v.bad {
  color: var(--el-color-danger);
}
.stat .n {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.boxes {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.box.bad {
  border-color: var(--el-color-danger-light-5);
  background: var(--el-color-danger-light-9);
}
.rules {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rule {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.rule.off {
  opacity: 0.55;
}
.rule.exclude {
  border-style: dashed;
  border-color: #e5a88a;
}
.line {
  font-size: 13px;
}
.lbl {
  display: inline-block;
  width: 72px;
  color: var(--el-text-color-secondary);
}
.chip {
  display: inline-block;
  margin: 2px 6px 2px 0;
  padding: 1px 8px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
}
.chip.kw {
  background: #fff4ed;
  color: #9a3412;
}
.chip.x {
  text-decoration: line-through;
}
.settings {
  max-width: 680px;
}
.rule-edit {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.rule-form {
  flex: 1;
  min-width: 0;
}
.pv {
  flex: 0 0 340px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.chat {
  display: flex;
  gap: 10px;
  padding: 12px;
  border-radius: 8px;
  background: #edeff2;
}
.bot {
  flex: none;
  width: 36px;
  height: 36px;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bubble {
  min-width: 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fff;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-all;
}
.bubble .q {
  padding-left: 8px;
  border-left: 3px solid #d1d5db;
  color: var(--el-text-color-regular);
}
.warn {
  color: #c2410c;
  font-weight: 700;
}
.fl {
  float: left;
}
@media (max-width: 900px) {
  .stats,
  .boxes {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .rule-edit {
    flex-direction: column;
  }
  .pv {
    flex-basis: auto;
    width: 100%;
  }
}
</style>
