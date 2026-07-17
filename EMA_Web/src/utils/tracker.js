import http from '../api/http'
import { getToken } from '../api/auth'
import { formatClientAt } from './datetime'

const KEY = 'ema_behavior_logs'
const META_KEY = 'ema_behavior_meta'
const MAX = 800
const pendingQueue = []
/** 上报队列：合并短时间内的打点，避免与路由抢网络 */
const uploadQueue = []
let uploadTimer = null

function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    if (raw == null) return fallback
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

function updateMeta(module, action, extra) {
  const meta = readJson(META_KEY, {
    openCount: 0,
    checkinTimes: [],
    diaryWordCounts: [],
    voiceDurations: [],
    videoDurations: [],
    taskDurations: [],
    videoSkips: 0,
    voiceSkips: 0,
  })
  if (action === 'app_launch' || (action === 'view' && module === 'app')) meta.openCount++
  if (action === 'submit' && module === 'questionnaire') {
    meta.checkinTimes.push({
      at: Date.now(),
      hour: new Date().getHours(),
      sessionId: extra?.sessionId || 1,
    })
  }
  if (action === 'session_complete' && module === 'checkin') {
    meta.checkinSessions = meta.checkinSessions || []
    meta.checkinSessions.push({
      at: Date.now(),
      sessionId: extra?.sessionId,
      date: extra?.date,
    })
  }
  if (action === 'recheckin_start' && module === 'home') {
    meta.recheckinCount = (meta.recheckinCount || 0) + 1
  }
  if (action === 'submit' && module === 'diary' && extra?.length) {
    meta.diaryWordCounts.push(extra.length)
  }
  if (action === 'submit' && module === 'voice' && extra?.duration) {
    meta.voiceDurations.push(extra.duration)
  }
  if (action === 'submit' && module === 'video' && extra?.duration) {
    meta.videoDurations = meta.videoDurations || []
    meta.videoDurations.push(extra.duration)
  }
  if (action === 'task_duration' && extra) meta.taskDurations.push(extra)
  localStorage.setItem(META_KEY, JSON.stringify(meta))
}

function postBehaviorEvent(entry) {
  if (!getToken()) {
    pendingQueue.push(entry)
    return
  }
  const meta = readJson(META_KEY, {})
  http
    .post('/behavior/track-log', {
      module: entry.module,
      action: entry.action,
      extra: entry.extra || {},
      route: entry.route || '',
      hour: entry.hour,
      client_at: formatClientAt(entry.at),
      behavior_meta: meta,
    })
    .catch((err) => console.warn('行为打点上报失败', err))
}

function scheduleUpload() {
  if (uploadTimer != null) return
  uploadTimer = setTimeout(() => {
    uploadTimer = null
    const batch = uploadQueue.splice(0)
    batch.forEach((entry) => postBehaviorEvent(entry))
  }, 300)
}

export function flushPendingBehavior() {
  if (!pendingQueue.length && !uploadQueue.length) return
  const queue = pendingQueue.splice(0).concat(uploadQueue.splice(0))
  if (uploadTimer != null) {
    clearTimeout(uploadTimer)
    uploadTimer = null
  }
  queue.forEach((entry) => postBehaviorEvent(entry))
}

export function trackEvent(module, action, extra, route) {
  const entry = {
    module,
    action,
    extra: extra || {},
    route: route || (typeof window !== 'undefined' ? window.location.pathname : ''),
    hour: new Date().getHours(),
    at: Date.now(),
  }
  const logs = readJson(KEY, [])
  logs.unshift(entry)
  localStorage.setItem(KEY, JSON.stringify(logs.slice(0, MAX)))
  updateMeta(module, action, extra)
  uploadQueue.push(entry)
  scheduleUpload()
  return entry
}

export function startTaskTimer(pageRoute) {
  localStorage.setItem('ema_task_timer', JSON.stringify({ route: pageRoute, start: Date.now() }))
}

export function endTaskTimer(module) {
  const raw = localStorage.getItem('ema_task_timer')
  if (!raw) return 0
  try {
    const t = JSON.parse(raw)
    if (t?.start) {
      const ms = Date.now() - t.start
      trackEvent(module, 'task_duration', { ms, route: t.route })
      localStorage.removeItem('ema_task_timer')
      return ms
    }
  } catch {
    /* ignore */
  }
  return 0
}

export function getBehaviorMeta() {
  return readJson(META_KEY, {})
}

export function getBehaviorLogs() {
  return readJson(KEY, [])
}
