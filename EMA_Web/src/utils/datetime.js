/** 与 EMA_WeChat/utils/datetime.js formatClientAt 一致 */
export function formatClientAt(ms) {
  const d = ms ? new Date(ms) : new Date()
  const pad = (n) => (n < 10 ? `0${n}` : String(n))
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  )
}

/** 与小程序知情同意页 formatConsentTime 一致 */
export function formatConsentTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const min = d.getMinutes()
  return (
    `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ` +
    `${d.getHours()}:${min < 10 ? '0' : ''}${min}`
  )
}
