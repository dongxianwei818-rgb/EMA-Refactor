import http from '../api/http'
import { getToken } from '../api/auth'
import { formatClientAt } from './datetime'
import { getStore } from './sessionStore'

const MAX = 800
const pendingQueue = []
const uploadQueue = []
let uploadTimer = null
/** 当前页任务计时（仅内存，不写 localStorage） */
let taskTimer = null

function getMeta() {
  return getStore().behaviorMeta || {}
}

function setMeta(meta) {
  getStore().behaviorMeta = meta
}

function getLogs() {
  return Array.isArray(getStore().behaviorLogs) ? getStore().behaviorLogs : []
}

function setLogs(logs) {
  getStore().behaviorLogs = logs
}

function updateMeta(module, action, extra) {
  const meta = {
    openCount: 0,
    checkinTimes: [],
    diaryWordCounts: [],
    voiceDurations: [],
    videoDurations: [],
    taskDurations: [],
    videoSkips: 0,
    voiceSkips: 0,
    ...getMeta(),
  }
  if (action === 'app_launch' || (action === 'view' && module === 'app')) meta.openCount++
  if (action === 'submit' && module === 'questionnaire') {
    meta.checkinTimes = meta.checkinTimes || []
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
    meta.diaryWordCounts = meta.diaryWordCounts || []
    meta.diaryWordCounts.push(extra.length)
  }
  if (action === 'submit' && module === 'voice' && extra?.duration) {
    meta.voiceDurations = meta.voiceDurations || []
    meta.voiceDurations.push(extra.duration)
  }
  if (action === 'submit' && module === 'video' && extra?.duration) {
    meta.videoDurations = meta.videoDurations || []
    meta.videoDurations.push(extra.duration)
  }
  if (action === 'task_duration' && extra) {
    meta.taskDurations = meta.taskDurations || []
    meta.taskDurations.push(extra)
  }
  setMeta(meta)
}

function postBehaviorEvent(entry) {
  if (!getToken()) {
    pendingQueue.push(entry)
    return
  }
  http
    .post('/behavior/track-log', {
      module: entry.module,
      action: entry.action,
      extra: entry.extra || {},
      route: entry.route || '',
      hour: entry.hour,
      client_at: formatClientAt(entry.at),
      behavior_meta: getMeta(),
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
  const logs = getLogs()
  logs.unshift(entry)
  setLogs(logs.slice(0, MAX))
  updateMeta(module, action, extra)
  uploadQueue.push(entry)
  scheduleUpload()
  return entry
}

export function startTaskTimer(pageRoute) {
  taskTimer = { route: pageRoute, start: Date.now() }
}

export function endTaskTimer(module) {
  if (!taskTimer?.start) return 0
  const ms = Date.now() - taskTimer.start
  const route = taskTimer.route
  taskTimer = null
  trackEvent(module, 'task_duration', { ms, route })
  return ms
}

export function getBehaviorMeta() {
  return getMeta()
}

export function getBehaviorLogs() {
  return getLogs()
}

/** 用服务端拉取的行为数据覆盖会话仓 */
export function replaceBehaviorFromServer(meta, logs) {
  if (meta && typeof meta === 'object') {
    setMeta(meta)
  }
  if (Array.isArray(logs)) {
    setLogs(logs.slice(0, MAX))
  }
}
