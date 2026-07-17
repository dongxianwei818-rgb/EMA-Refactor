/**
 * EMA 本地状态（对齐 EMA_WeChat/utils/ema.js，使用 localStorage）
 */
import {
  TASK_ORDER,
  TASK_ROUTES,
  VIDEO_INTERVAL_DAYS,
  VOICE_INTERVAL_DAYS,
} from '../constants/ema'
import { getServerProfile, hasConsent, setServerProfile } from './consentState'
import { notifySessionCompleted, notifySessionStarted } from './checkin'
import { trackEvent } from './tracker'

const KEY = {
  BASELINE: 'ema_baseline',
  DAILY: 'ema_daily_tasks',
  VIDEO_DATES: 'ema_video_dates',
  SUBMISSIONS: 'ema_submissions',
  STEPS_HISTORY: 'ema_steps_history',
  STEPS_BASELINE: 'ema_steps_baseline',
  VIDEO_SKIPS: 'ema_video_skips',
  VOICE_SKIPS: 'ema_voice_skips',
  CHECKIN_DAY: 'ema_checkin_day',
}

const SKIP_MAX = 500
const MS_PER_DAY = 24 * 60 * 60 * 1000

function lsGet(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    if (raw == null) return fallback
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

function lsSet(key, value) {
  localStorage.setItem(key, JSON.stringify(value))
}

export function getTodayKey(d = new Date()) {
  const m = d.getMonth() + 1
  const day = d.getDate()
  return `${d.getFullYear()}-${m < 10 ? '0' : ''}${m}-${day < 10 ? '0' : ''}${day}`
}

export function isResearchBound() {
  const server = getServerProfile()
  if (server.research_id || server.has_baseline) return true
  const profile = getProfile()
  return !!(profile.researchId || profile.research_id)
}

export function hasBaseline() {
  return !!localStorage.getItem(KEY.BASELINE)
}

export function isOnboardingComplete() {
  return hasConsent() && isResearchBound()
}

export function saveBaseline(data) {
  const payload = { ...data, at: data.at || Date.now() }
  if (payload.research_id && !payload.researchId) {
    payload.researchId = payload.research_id
  }
  lsSet(KEY.BASELINE, payload)
  lsSet('ema_profile', payload)
}

export function getProfile() {
  return lsGet('ema_profile', lsGet(KEY.BASELINE, {}))
}

/** 本地无完整基线字段时，从服务端 sync/pull 回填；force 时始终拉取 */
export async function ensureBaselineProfile(options = {}) {
  const force = !!options.force
  const local = getProfile() || {}
  const hasBasic =
    local.age != null &&
    local.age !== '' &&
    (local.researchId || local.research_id || local.gender)
  if (hasBasic && !force) {
    return {
      ...local,
      researchId: local.researchId || local.research_id || '',
    }
  }
  try {
    const { syncPull } = await import('../api/ema')
    const data = await syncPull()
    if (data?.baseline) {
      const baseline = {
        ...data.baseline,
        researchId:
          data.baseline.researchId ||
          data.baseline.research_id ||
          data.research_id ||
          '',
        at: data.baseline.at || Date.now(),
      }
      saveBaseline(baseline)
      const sp = getServerProfile()
      if (baseline.researchId) {
        sp.research_id = baseline.researchId
        sp.has_baseline = true
        setServerProfile(sp)
      }
      return getProfile()
    }
  } catch (err) {
    console.warn('拉取基线档案失败', err)
  }
  return {
    ...local,
    researchId: local.researchId || local.research_id || getServerProfile().research_id || '',
  }
}

function dailyStore() {
  return lsGet(KEY.DAILY, {})
}

function saveDailyStore(store) {
  lsSet(KEY.DAILY, store)
}

export function getTodayTasks() {
  const store = dailyStore()
  const t = getTodayKey()
  return (
    store[t] || {
      questionnaire: false,
      diary: false,
      voice: false,
      video: false,
      steps: false,
      videoSkipped: false,
      voiceSkipped: false,
    }
  )
}

export function applyDailyTasksResponse(data) {
  if (!data) return
  if (data.daily_tasks && typeof data.daily_tasks === 'object') {
    const store = dailyStore()
    Object.keys(data.daily_tasks).forEach((dateKey) => {
      store[dateKey] = data.daily_tasks[dateKey]
    })
    saveDailyStore(store)
    return
  }
  const tasks = data.tasks
  const taskDate = data.task_date
  if (!tasks || !taskDate) return
  const defaults = {
    questionnaire: false,
    diary: false,
    voice: false,
    video: false,
    steps: false,
    videoSkipped: false,
    voiceSkipped: false,
  }
  const store = dailyStore()
  store[taskDate] = { ...defaults, ...(store[taskDate] || {}), ...tasks }
  saveDailyStore(store)
}

export function resetTodayTasks() {
  const store = dailyStore()
  store[getTodayKey()] = {
    questionnaire: false,
    diary: false,
    voice: false,
    video: false,
    steps: false,
    videoSkipped: false,
    voiceSkipped: false,
  }
  saveDailyStore(store)
}

function getCheckinDayState() {
  const state = lsGet(KEY.CHECKIN_DAY, null)
  const today = getTodayKey()
  if (!state || state.date !== today) {
    return { date: today, sessionId: 1, sessions: [] }
  }
  return state
}

function saveCheckinDayState(state) {
  lsSet(KEY.CHECKIN_DAY, state)
}

export function getCurrentSessionId() {
  return getCheckinDayState().sessionId
}

export function ensureCheckinSession() {
  const state = getCheckinDayState()
  const found = state.sessions.some((s) => s.id === state.sessionId)
  if (!found) {
    const startedAt = Date.now()
    state.sessions.push({ id: state.sessionId, startedAt, completedAt: null })
    saveCheckinDayState(state)
    notifySessionStarted(state.sessionId, startedAt, state.date)
  }
  return state.sessionId
}

function completeCurrentSession() {
  const state = getCheckinDayState()
  let session = state.sessions.find((s) => s.id === state.sessionId)
  if (!session) {
    session = { id: state.sessionId, startedAt: Date.now(), completedAt: null }
    state.sessions.push(session)
  }
  if (!session.completedAt) {
    session.completedAt = Date.now()
    saveCheckinDayState(state)
    notifySessionCompleted(state.sessionId, session.completedAt, state.date)
  }
  return session
}

function maybeCompleteSession() {
  if (!isTodayCheckinComplete()) return
  const state = getCheckinDayState()
  const session = state.sessions.find((s) => s.id === state.sessionId)
  if (session?.completedAt) return
  completeCurrentSession()
  trackEvent('checkin', 'session_complete', {
    sessionId: session?.id || getCheckinDayState().sessionId,
    date: getTodayKey(),
  })
}

export function isTodayCheckinComplete() {
  const progress = getTaskProgress()
  return progress.done >= progress.total
}

export function startRecheckin() {
  const state = getCheckinDayState()
  if (isTodayCheckinComplete()) completeCurrentSession()
  const startedAt = Date.now()
  state.sessionId += 1
  state.sessions.push({ id: state.sessionId, startedAt, completedAt: null })
  saveCheckinDayState(state)
  resetTodayTasks()
  notifySessionStarted(state.sessionId, startedAt, state.date)
  return state.sessionId
}

export function getTodayCheckinSessions() {
  return getCheckinDayState().sessions
}

export function markTaskDone(task) {
  ensureCheckinSession()
  const store = dailyStore()
  const t = getTodayKey()
  const tasks = { ...getTodayTasks(), [task]: true }
  store[t] = tasks
  saveDailyStore(store)
  maybeCompleteSession()
  return tasks
}

function normalizeSkipList(raw) {
  if (!raw) return []
  return Array.isArray(raw) ? raw : []
}

function recordSkip(type, extra) {
  ensureCheckinSession()
  const key = type === 'video' ? KEY.VIDEO_SKIPS : KEY.VOICE_SKIPS
  const at = Date.now()
  const list = normalizeSkipList(lsGet(key, []))
  list.unshift({
    at,
    date: getTodayKey(),
    sessionId: getCurrentSessionId(),
    reason: extra?.reason || 'skip',
  })
  lsSet(key, list.slice(0, SKIP_MAX))
  return at
}

export function markVideoSkipped(extra) {
  const tasks = markTaskDone('video')
  tasks.videoSkipped = true
  const store = dailyStore()
  store[getTodayKey()] = tasks
  saveDailyStore(store)
  const at = recordSkip('video', extra)
  saveSubmission('video', { skip: true, reason: extra?.reason || 'skip' }, { at })
}

export function markVoiceSkipped(extra) {
  const tasks = markTaskDone('voice')
  tasks.voiceSkipped = true
  const store = dailyStore()
  store[getTodayKey()] = tasks
  saveDailyStore(store)
  const at = recordSkip('voice', extra)
  saveSubmission('voice', { skip: true, reason: extra?.reason || 'skip' }, { at })
}

export function getVideoSkips() {
  return normalizeSkipList(lsGet(KEY.VIDEO_SKIPS, []))
}

export function getVoiceSkips() {
  return normalizeSkipList(lsGet(KEY.VOICE_SKIPS, []))
}

export function getVideoSkipCount() {
  return getVideoSkips().length
}

export function getVoiceSkipCount() {
  return getVoiceSkips().length
}

export function getMissedDays() {
  const store = dailyStore()
  let missed = 0
  for (let i = 1; i <= 14; i++) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const k = getTodayKeyFromDate(d)
    const t = store[k]
    if (!t || !t.questionnaire) missed++
    else break
  }
  return missed
}

function getTodayKeyFromDate(d) {
  const m = d.getMonth() + 1
  const day = d.getDate()
  return `${d.getFullYear()}-${m < 10 ? '0' : ''}${m}-${day < 10 ? '0' : ''}${day}`
}

export function saveSubmission(type, payload, meta = {}) {
  ensureCheckinSession()
  const list = lsGet(KEY.SUBMISSIONS, [])
  list.unshift({
    type,
    payload: payload || {},
    date: meta.date || getTodayKey(),
    at: meta.at || Date.now(),
    sessionId: meta.sessionId != null ? meta.sessionId : getCurrentSessionId(),
  })
  lsSet(KEY.SUBMISSIONS, list.slice(0, 300))
}

export function getSubmissions() {
  return lsGet(KEY.SUBMISSIONS, [])
}

function getLastSubmissionAt(type) {
  const list = getSubmissions()
  for (const item of list) {
    if (item.type === type && item.at) return item.at
  }
  return null
}

export function getRecordingIntervalStatus(type) {
  const intervalDays = type === 'voice' ? VOICE_INTERVAL_DAYS : VIDEO_INTERVAL_DAYS
  const lastAt = getLastSubmissionAt(type)
  if (!lastAt) {
    return { due: true, intervalDays, daysSince: null, daysRemaining: 0, lastAt: null }
  }
  const elapsedDays = (Date.now() - lastAt) / MS_PER_DAY
  const due = elapsedDays >= intervalDays
  const daysRemaining = due ? 0 : Math.ceil(intervalDays - elapsedDays)
  return {
    due,
    intervalDays,
    daysSince: Math.floor(elapsedDays),
    daysRemaining,
    lastAt,
  }
}

export function shouldShowVoiceTask() {
  const tasks = getTodayTasks()
  return !tasks.voice && !tasks.voiceSkipped
}

export function shouldShowVideoTask() {
  const tasks = getTodayTasks()
  return !tasks.video && !tasks.videoSkipped
}

export function getTaskRoute(taskKey) {
  return TASK_ROUTES[taskKey] || null
}

export function getNextTaskRoute() {
  const tasks = getTodayTasks()
  for (const task of TASK_ORDER) {
    if (tasks[task]) continue
    if (task === 'voice' && !shouldShowVoiceTask()) continue
    if (task === 'video' && !shouldShowVideoTask()) continue
    return TASK_ROUTES[task]
  }
  return null
}

export function getTaskProgress() {
  const tasks = getTodayTasks()
  let done = 0
  const total = TASK_ORDER.length
  TASK_ORDER.forEach((t) => {
    if (tasks[t]) done++
    else if (t === 'voice' && !shouldShowVoiceTask()) done++
    else if (t === 'video' && !shouldShowVideoTask()) done++
  })
  return { done, total, tasks, percent: Math.round((done / total) * 100) }
}

export function saveStepsHistory(steps) {
  const hist = lsGet(KEY.STEPS_HISTORY, [])
  const today = getTodayKey()
  const filtered = hist.filter((h) => h.date !== today)
  filtered.unshift({ date: today, steps, at: Date.now() })
  lsSet(KEY.STEPS_HISTORY, filtered.slice(0, 90))
  if (!localStorage.getItem(KEY.STEPS_BASELINE) && filtered.length >= 3) {
    let sum = 0
    const count = Math.min(7, filtered.length)
    for (let i = 0; i < count; i++) sum += filtered[i].steps
    lsSet(KEY.STEPS_BASELINE, Math.round(sum / count))
  }
}

export function getStepsAnalytics() {
  const hist = lsGet(KEY.STEPS_HISTORY, [])
  const baseline = lsGet(KEY.STEPS_BASELINE, 0)
  const today = hist[0]?.steps || 0
  let sum7 = 0
  const count7 = Math.min(7, hist.length)
  for (let i = 0; i < count7; i++) sum7 += hist[i].steps
  const avg7 = count7 ? Math.round(sum7 / count7) : 0
  let lowDays = 0
  const threshold = baseline ? baseline * 0.4 : 2000
  for (let j = 0; j < hist.length && j < 14; j++) {
    if (hist[j].steps < threshold) lowDays++
    else break
  }
  const deviation = baseline && today ? Math.round(((today - baseline) / baseline) * 100) : 0
  return { today, avg7, baseline, lowDays, deviation, hist }
}

export function markVideoDone() {
  const dates = lsGet(KEY.VIDEO_DATES, [])
  dates.push(Date.now())
  lsSet(KEY.VIDEO_DATES, dates)
}

export function bindResearchFromBaseline(data, form) {
  const sp = getServerProfile()
  sp.research_id = data?.research_id || data?.researchId || form?.researchId
  sp.has_baseline = true
  setServerProfile(sp)
  const merged = {
    ...(form || {}),
    ...(data || {}),
    researchId: data?.researchId || data?.research_id || form?.researchId || '',
    at: data?.at || Date.now(),
  }
  // 去掉接口元数据，只保留档案字段
  delete merged.token
  delete merged.participation_recreated
  delete merged.user_id
  delete merged.openid
  delete merged.user_name
  delete merged.completed_at
  saveBaseline(merged)
}
