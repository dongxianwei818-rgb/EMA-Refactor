import http from '../api/http'
import { formatClientAt } from './datetime'
import { getStore } from './sessionStore'

function getCheckinDaySnapshot() {
  return getStore().checkinDay
}

export function startCheckinSession(sessionId, startedAtMs, taskDate) {
  return http.post('/checkin/session/start', {
    task_date: taskDate,
    session_id: sessionId || 1,
    started_at: formatClientAt(startedAtMs),
    checkin_day: getCheckinDaySnapshot(),
  })
}

export function completeCheckinSession(sessionId, completedAtMs, taskDate) {
  return http.post('/checkin/session/complete', {
    task_date: taskDate,
    session_id: sessionId || 1,
    completed_at: formatClientAt(completedAtMs),
    checkin_day: getCheckinDaySnapshot(),
  })
}

export function notifySessionStarted(sessionId, startedAtMs, taskDate) {
  startCheckinSession(sessionId, startedAtMs, taskDate).catch((err) => {
    console.warn('记录打卡会话失败', err)
  })
}

export function notifySessionCompleted(sessionId, completedAtMs, taskDate) {
  completeCheckinSession(sessionId, completedAtMs, taskDate).catch((err) => {
    console.warn('记录打卡完成失败', err)
  })
}
