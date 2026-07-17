/**
 * EMA 会话状态：业务数据保存在内存（sessionStore），由 sync/pull 等接口填充。
 * 换终端登录后以服务端数据为准；localStorage 不存业务数据。
 */
import {
  TASK_ORDER,
  TASK_ROUTES,
  VIDEO_INTERVAL_DAYS,
  VOICE_INTERVAL_DAYS,
} from '../constants/ema'
import { getServerProfile, hasConsent, setServerProfile } from './consentState'
import { notifySessionCompleted, notifySessionStarted } from './checkin'
import { getStore } from './sessionStore'
import { replaceBehaviorFromServer, trackEvent } from './tracker'

const SKIP_MAX = 500
const MS_PER_DAY = 24 * 60 * 60 * 1000

const EMPTY_TASKS = () => ({
  questionnaire: false,
  diary: false,
  voice: false,
  video: false,
  steps: false,
  videoSkipped: false,
  voiceSkipped: false,
})

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
  const p = getProfile()
  return !!(p && (p.researchId || p.research_id || p.age != null))
}

export function isOnboardingComplete() {
  return hasConsent() && isResearchBound()
}

export function saveBaseline(data) {
  const payload = { ...data, at: data.at || Date.now() }
  if (payload.research_id && !payload.researchId) {
    payload.researchId = payload.research_id
  }
  getStore().baseline = payload
}

export function getProfile() {
  return getStore().baseline || {}
}

/** 将 sync/pull 返回写入内存会话仓 */
export function applySyncPullPayload(data) {
  if (!data || typeof data !== 'object') return
  const store = getStore()

  if (data.baseline) {
    saveBaseline({
      ...data.baseline,
      researchId:
        data.baseline.researchId ||
        data.baseline.research_id ||
        data.research_id ||
        '',
      at: data.baseline.at || Date.now(),
    })
  } else if (data.research_id) {
    const local = getProfile() || {}
    if (!local.researchId && !local.research_id) {
      saveBaseline({ ...local, researchId: data.research_id, at: local.at || Date.now() })
    }
  }

  if (data.daily_tasks && typeof data.daily_tasks === 'object') {
    applyDailyTasksResponse({ daily_tasks: data.daily_tasks })
  }

  if (data.checkin_day && typeof data.checkin_day === 'object') {
    const today = getTodayKey()
    if (data.checkin_day.date === today || !data.checkin_day.date) {
      const incoming = {
        date: data.checkin_day.date || today,
        sessionId: Number(data.checkin_day.sessionId || data.checkin_day.session_id || 1),
        sessions: Array.isArray(data.checkin_day.sessions)
          ? data.checkin_day.sessions.map((s) => ({
              id: Number(s.id),
              startedAt: s.startedAt || s.started_at || null,
              completedAt: s.completedAt ?? s.completed_at ?? null,
            }))
          : [],
      }
      const local = store.checkinDay
      if (local && local.date === incoming.date) {
        const byId = new Map()
        ;[...(local.sessions || []), ...incoming.sessions].forEach((s) => {
          if (!s?.id) return
          const prev = byId.get(s.id)
          byId.set(s.id, {
            id: s.id,
            startedAt: s.startedAt || prev?.startedAt || null,
            completedAt:
              s.completedAt != null
                ? s.completedAt
                : prev?.completedAt != null
                  ? prev.completedAt
                  : null,
          })
        })
        const sessions = Array.from(byId.values()).sort((a, b) => a.id - b.id)
        const maxId = Math.max(
          Number(local.sessionId) || 1,
          Number(incoming.sessionId) || 1,
          ...sessions.map((s) => s.id),
          1,
        )
        store.checkinDay = { date: today, sessionId: maxId, sessions }
      } else {
        store.checkinDay = incoming
      }
    }
  }

  if (Array.isArray(data.submissions)) {
    store.submissions = data.submissions.map((s) => ({
      type: s.type,
      payload: s.payload || {},
      date: s.date,
      at: s.at || Date.now(),
      sessionId: s.sessionId != null ? s.sessionId : s.session_id || 1,
    }))
  }

  if (Array.isArray(data.steps_history)) {
    store.stepsHistory = data.steps_history
  }
  if (data.steps_baseline != null) {
    store.stepsBaseline = data.steps_baseline
  }

  if (Array.isArray(data.video_skips)) {
    store.videoSkips = data.video_skips
  }
  if (Array.isArray(data.voice_skips)) {
    store.voiceSkips = data.voice_skips
  }
  if (Array.isArray(data.video_dates)) {
    store.videoDates = data.video_dates
  }

  replaceBehaviorFromServer(data.behavior_meta, data.behavior_logs)
}

/** 内存无完整基线时从服务端拉取 */
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
    applySyncPullPayload(data)
    const sp = getServerProfile()
    if (data?.research_id || data?.baseline) {
      sp.research_id =
        data.research_id ||
        data.baseline?.researchId ||
        data.baseline?.research_id ||
        sp.research_id
      if (sp.research_id) sp.has_baseline = true
      setServerProfile(sp)
    }
    const profile = getProfile() || {}
    return {
      ...profile,
      researchId: profile.researchId || profile.research_id || sp.research_id || '',
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
  return getStore().dailyTasks || {}
}

function saveDailyStore(store) {
  getStore().dailyTasks = store
}

export function getTodayTasks() {
  const store = dailyStore()
  const t = getTodayKey()
  return store[t] || EMPTY_TASKS()
}

export function applyDailyTasksResponse(data) {
  if (!data) return
  if (data.daily_tasks && typeof data.daily_tasks === 'object') {
    const store = { ...dailyStore() }
    Object.keys(data.daily_tasks).forEach((dateKey) => {
      store[dateKey] = data.daily_tasks[dateKey]
    })
    saveDailyStore(store)
    return
  }
  const tasks = data.tasks
  const taskDate = data.task_date
  if (!tasks || !taskDate) return
  const store = { ...dailyStore() }
  store[taskDate] = { ...EMPTY_TASKS(), ...(store[taskDate] || {}), ...tasks }
  saveDailyStore(store)
}

export function resetTodayTasks() {
  const store = { ...dailyStore() }
  store[getTodayKey()] = EMPTY_TASKS()
  saveDailyStore(store)
}

function getCheckinDayState() {
  const today = getTodayKey()
  let state = getStore().checkinDay
  if (!state || state.date !== today) {
    state = { date: today, sessionId: 1, sessions: [] }
    getStore().checkinDay = state
  }
  if (!Array.isArray(state.sessions)) state.sessions = []
  if (!state.sessionId || state.sessionId < 1) state.sessionId = 1
  return state
}

function saveCheckinDayState(state) {
  getStore().checkinDay = state
}

/** 供 checkin API 上报当前会话快照 */
export function getCheckinDaySnapshot() {
  return getStore().checkinDay
}

export function getCurrentSessionId() {
  return getCheckinDayState().sessionId
}

function maxSessionIdInState(state) {
  const ids = [Number(state.sessionId) || 1]
  ;(state.sessions || []).forEach((s) => {
    const id = Number(s?.id)
    if (id >= 1) ids.push(id)
  })
  return Math.max(...ids)
}

export function ensureCheckinSession() {
  const state = getCheckinDayState()
  const found = state.sessions.some((s) => s.id === state.sessionId)
  if (!found) {
    const startedAt = Date.now()
    state.sessions.push({ id: state.sessionId, startedAt, completedAt: null })
    saveCheckinDayState(state)
    notifySessionStarted(state.sessionId, startedAt, state.date)
  } else {
    saveCheckinDayState(state)
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

/**
 * 重新打卡：sessionId = 当日已有最大 session + 1，并与 checkin_sessions 对齐。
 * @returns {Promise<number>} 新的 sessionId
 */
export async function startRecheckin() {
  const { startCheckinSession, completeCheckinSession } = await import('./checkin')
  const state = getCheckinDayState()

  if (isTodayCheckinComplete()) {
    const finished = completeCurrentSession()
    try {
      await completeCheckinSession(finished.id, finished.completedAt, state.date)
    } catch (err) {
      console.warn('完成上一轮打卡会话失败', err)
    }
  }

  const nextId = maxSessionIdInState(state) + 1
  const startedAt = Date.now()
  state.sessionId = nextId
  if (!state.sessions.some((s) => s.id === nextId)) {
    state.sessions.push({ id: nextId, startedAt, completedAt: null })
  }
  saveCheckinDayState(state)
  resetTodayTasks()

  try {
    const data = await startCheckinSession(nextId, startedAt, state.date)
    const { invalidateHydrateCache } = await import('./sessionStore')
    invalidateHydrateCache()
    const serverSid = Number(data?.session_id)
    if (serverSid >= 1 && serverSid !== nextId) {
      // 以服务端为准（极少见）
      state.sessionId = serverSid
      const row = state.sessions.find((s) => s.id === nextId)
      if (row) row.id = serverSid
      saveCheckinDayState(state)
      return serverSid
    }
  } catch (err) {
    console.warn('创建新打卡会话失败', err)
  }
  return state.sessionId
}

export function getTodayCheckinSessions() {
  return getCheckinDayState().sessions
}

export function markTaskDone(task) {
  ensureCheckinSession()
  const store = { ...dailyStore() }
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
  const store = getStore()
  const at = Date.now()
  const list = normalizeSkipList(type === 'video' ? store.videoSkips : store.voiceSkips)
  list.unshift({
    at,
    date: getTodayKey(),
    sessionId: getCurrentSessionId(),
    reason: extra?.reason || 'skip',
  })
  const trimmed = list.slice(0, SKIP_MAX)
  if (type === 'video') store.videoSkips = trimmed
  else store.voiceSkips = trimmed
  return at
}

export function markVideoSkipped(extra) {
  const tasks = markTaskDone('video')
  tasks.videoSkipped = true
  const store = { ...dailyStore() }
  store[getTodayKey()] = tasks
  saveDailyStore(store)
  const at = recordSkip('video', extra)
  saveSubmission('video', { skip: true, reason: extra?.reason || 'skip' }, { at })
}

export function markVoiceSkipped(extra) {
  const tasks = markTaskDone('voice')
  tasks.voiceSkipped = true
  const store = { ...dailyStore() }
  store[getTodayKey()] = tasks
  saveDailyStore(store)
  const at = recordSkip('voice', extra)
  saveSubmission('voice', { skip: true, reason: extra?.reason || 'skip' }, { at })
}

export function getVideoSkips() {
  return normalizeSkipList(getStore().videoSkips)
}

export function getVoiceSkips() {
  return normalizeSkipList(getStore().voiceSkips)
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
  const store = getStore()
  const list = Array.isArray(store.submissions) ? store.submissions.slice() : []
  list.unshift({
    type,
    payload: payload || {},
    date: meta.date || getTodayKey(),
    at: meta.at || Date.now(),
    sessionId: meta.sessionId != null ? meta.sessionId : getCurrentSessionId(),
  })
  store.submissions = list.slice(0, 300)
}

export function getSubmissions() {
  return Array.isArray(getStore().submissions) ? getStore().submissions : []
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
  const store = getStore()
  const hist = Array.isArray(store.stepsHistory) ? store.stepsHistory.slice() : []
  const today = getTodayKey()
  const filtered = hist.filter((h) => h.date !== today)
  filtered.unshift({ date: today, steps, at: Date.now() })
  store.stepsHistory = filtered.slice(0, 90)
  if (!store.stepsBaseline && filtered.length >= 3) {
    let sum = 0
    const count = Math.min(7, filtered.length)
    for (let i = 0; i < count; i++) sum += filtered[i].steps
    store.stepsBaseline = Math.round(sum / count)
  }
}

export function getStepsAnalytics() {
  const store = getStore()
  const hist = Array.isArray(store.stepsHistory) ? store.stepsHistory : []
  const baseline = store.stepsBaseline || 0
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
  const store = getStore()
  const dates = Array.isArray(store.videoDates) ? store.videoDates.slice() : []
  dates.push(Date.now())
  store.videoDates = dates
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
  delete merged.token
  delete merged.participation_recreated
  delete merged.user_id
  delete merged.openid
  delete merged.user_name
  delete merged.completed_at
  saveBaseline(merged)
}
