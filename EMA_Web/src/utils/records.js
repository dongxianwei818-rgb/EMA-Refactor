import { getSubmissions, getVideoSkips, getVoiceSkips, getTodayKey, getTodayCheckinSessions } from './ema'
import { getStore } from './sessionStore'
import { EMA_QUESTIONS } from '../constants/ema'

const LABELS = {
  questionnaire: 'EMA 问卷',
  diary: '文本日记',
  voice: '语音任务',
  video: '视频任务',
  steps: '运动步数',
}

const TYPE_ORDER = ['questionnaire', 'diary', 'voice', 'video', 'steps']

function formatDateLabel(dateStr) {
  const parts = dateStr.split('-')
  if (parts.length !== 3) return dateStr
  return `${parts[0]}年${Number(parts[1])}月${Number(parts[2])}日`
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const h = d.getHours()
  const m = d.getMinutes()
  return `${h < 10 ? '0' : ''}${h}:${m < 10 ? '0' : ''}${m}`
}

function buildQuestionnaireDetails(payload = {}) {
  const answers = payload.answers || {}
  return EMA_QUESTIONS.map((q) => {
    const raw = answers[q.id]
    if (raw === undefined || raw === null || raw === '') return null
    const value = q.type === 'scale10' ? `${raw}/10` : String(raw)
    return { id: q.id, label: q.label, value }
  }).filter(Boolean)
}

function buildItemSummary(item) {
  const p = item.payload || {}
  switch (item.type) {
    case 'diary':
      return p.text || '（无内容）'
    case 'steps':
      return `步数 ${p.steps != null ? p.steps : '--'}`
    case 'questionnaire': {
      const details = buildQuestionnaireDetails(p)
      const duration =
        p.durationSec != null ? `完成用时 ${p.durationSec} 秒` : ''
      if (details.length) {
        return duration || `共 ${details.length} 题作答`
      }
      return duration || '（无问卷内容）'
    }
    case 'voice':
      if (p.skip) return '语音跳过'
      return `录音时长 ${p.duration != null ? p.duration : '--'} 秒`
    case 'video':
      if (p.skip) return '视频跳过'
      return `视频时长 ${p.duration != null ? p.duration : '--'} 秒${p.hideFace ? ' · 不露脸' : ''}`
    default:
      return '已记录'
  }
}

function buildItemDetails(item) {
  if (item.type !== 'questionnaire') return []
  return buildQuestionnaireDetails(item.payload || {})
}

function hasSkipRecord(list, type, date, sessionId) {
  return list.some(
    (item) =>
      item.type === type &&
      item.date === date &&
      (item.sessionId || 1) === sessionId &&
      item.payload?.skip,
  )
}

function mergeSkipRecords(list) {
  const merged = list.slice()
  getVoiceSkips().forEach((item) => {
    const date = item.date || getTodayKey()
    const sessionId = item.sessionId || 1
    if (hasSkipRecord(merged, 'voice', date, sessionId)) return
    merged.push({
      type: 'voice',
      payload: { skip: true, reason: item.reason || 'skip' },
      date,
      at: item.at || Date.now(),
      sessionId,
    })
  })
  getVideoSkips().forEach((item) => {
    const date = item.date || getTodayKey()
    const sessionId = item.sessionId || 1
    if (hasSkipRecord(merged, 'video', date, sessionId)) return
    merged.push({
      type: 'video',
      payload: { skip: true, reason: item.reason || 'skip' },
      date,
      at: item.at || Date.now(),
      sessionId,
    })
  })
  return merged
}

/** 把当日 checkin_sessions 合并进列表，保证重新打卡后即使尚无采集项也能在记录页看到该轮 */
function mergeCheckinSessions(list) {
  const merged = list.slice()
  const today = getTodayKey()
  const day = getStore().checkinDay
  const sessions =
    day && day.date === today
      ? day.sessions || []
      : getTodayCheckinSessions()

  sessions.forEach((s) => {
    const sid = Number(s.id) || 1
    const exists = merged.some(
      (item) => item.date === today && (item.sessionId || 1) === sid,
    )
    if (exists) return
    merged.push({
      type: '_session',
      payload: { placeholder: true },
      date: today,
      at: s.startedAt || Date.now(),
      sessionId: sid,
    })
  })
  return merged
}

export function groupSubmissions(list) {
  const groups = {}
  list.forEach((item) => {
    const sid = item.sessionId || 1
    const key = `${item.date}_${sid}`
    if (!groups[key]) {
      groups[key] = {
        key,
        date: item.date,
        dateLabel: formatDateLabel(item.date),
        sessionId: sid,
        startedAt: item.at,
        endedAt: item.at,
        items: [],
      }
    }
    const g = groups[key]
    if (item.at) {
      if (!g.startedAt || item.at < g.startedAt) g.startedAt = item.at
      if (!g.endedAt || item.at > g.endedAt) g.endedAt = item.at
    }
    if (item.type === '_session') return
    g.items.push({
      id: `${item.type}_${item.at || 0}_${sid}`,
      type: item.type,
      typeLabel: LABELS[item.type] || item.type,
      summary: buildItemSummary(item),
      details: buildItemDetails(item),
      timeLabel: formatTime(item.at),
    })
  })

  const sessions = Object.values(groups)
  sessions.sort((a, b) => {
    if (a.date !== b.date) return a.date < b.date ? 1 : -1
    return b.sessionId - a.sessionId
  })

  sessions.forEach((s) => {
    s.items.sort((a, b) => TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type))
    s.itemCount = s.items.length
    if (!s.items.length) {
      s.timeRange = formatTime(s.startedAt)
    } else {
      s.timeRange =
        s.startedAt && s.endedAt && s.startedAt !== s.endedAt
          ? `${formatTime(s.startedAt)} – ${formatTime(s.endedAt)}`
          : formatTime(s.startedAt || s.endedAt)
    }
  })

  return sessions
}

export function loadRecordSessions() {
  const raw = mergeCheckinSessions(mergeSkipRecords(getSubmissions()))
  const realCount = raw.filter((r) => r.type !== '_session').length
  return { sessions: groupSubmissions(raw), totalCount: realCount }
}
