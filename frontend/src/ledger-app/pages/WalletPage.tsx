import { useMemo, useState, type FormEvent } from 'react'
import { WalletRecordsTable } from '../components/WalletRecordsTable'
import { formatBeijing } from '../lib/beijing'
import { api } from '../lib/api'
import { notifyWalletUpdated } from '../lib/ledgerEvents'
import {
  formatWalletMoneyOnBlur,
  parseWalletMoneySubmit,
  sanitizeWalletMoneyInput,
} from '../lib/walletAmountInput'

export function WalletPage() {
  const [wechat, setWechat] = useState('')
  const [alipay, setAlipay] = useState('')
  const [card, setCard] = useState('')
  const [pocket, setPocket] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [tableRefresh, setTableRefresh] = useState(0)

  const totalNum = useMemo(() => {
    return (
      parseWalletMoneySubmit(wechat) +
      parseWalletMoneySubmit(alipay) +
      parseWalletMoneySubmit(card) +
      parseWalletMoneySubmit(pocket)
    )
  }, [wechat, alipay, card, pocket])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setErr(null)
    setMsg(null)
    try {
      await api.walletCreate({
        recordAt: formatBeijing(),
        wechat: parseWalletMoneySubmit(wechat),
        alipay: parseWalletMoneySubmit(alipay),
        card: parseWalletMoneySubmit(card),
        pocket: parseWalletMoneySubmit(pocket),
      })
      setMsg('已保存')
      setWechat('')
      setAlipay('')
      setCard('')
      setPocket('')
      setTableRefresh((n) => n + 1)
      notifyWalletUpdated()
    } catch (e) {
      setErr((e as Error).message)
    }
  }

  return (
    <div className="page">
      <h1 className="page-title">钱包余额</h1>

      <form className="panel form-panel" onSubmit={submit}>
        <div className="row-5">
          <div className="field">
            <label htmlFor="w-wechat">微信</label>
            <input
              id="w-wechat"
              inputMode="decimal"
              autoComplete="off"
              value={wechat}
              onChange={(e) => setWechat(sanitizeWalletMoneyInput(e.target.value))}
              onBlur={() => setWechat(formatWalletMoneyOnBlur(wechat))}
            />
          </div>
          <div className="field">
            <label htmlFor="w-alipay">支付宝</label>
            <input
              id="w-alipay"
              inputMode="decimal"
              autoComplete="off"
              value={alipay}
              onChange={(e) => setAlipay(sanitizeWalletMoneyInput(e.target.value))}
              onBlur={() => setAlipay(formatWalletMoneyOnBlur(alipay))}
            />
          </div>
          <div className="field">
            <label htmlFor="w-card">卡片</label>
            <input
              id="w-card"
              inputMode="decimal"
              autoComplete="off"
              value={card}
              onChange={(e) => setCard(sanitizeWalletMoneyInput(e.target.value))}
              onBlur={() => setCard(formatWalletMoneyOnBlur(card))}
            />
          </div>
          <div className="field">
            <label htmlFor="w-pocket">小荷包</label>
            <input
              id="w-pocket"
              inputMode="decimal"
              autoComplete="off"
              value={pocket}
              onChange={(e) => setPocket(sanitizeWalletMoneyInput(e.target.value))}
              onBlur={() => setPocket(formatWalletMoneyOnBlur(pocket))}
            />
          </div>
          <div className="field">
            <label htmlFor="w-total">总计（自动）</label>
            <input id="w-total" readOnly className="readonly" value={(Math.round(totalNum * 100) / 100).toFixed(2)} />
          </div>
        </div>

        {err && <p className="error">{err}</p>}
        {msg && <p className="success">{msg}</p>}

        <button type="submit" className="btn primary">
          保存本条
        </button>
      </form>

      <WalletRecordsTable refreshTrigger={tableRefresh} onChanged={notifyWalletUpdated} />
    </div>
  )
}
