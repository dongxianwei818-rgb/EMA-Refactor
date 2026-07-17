import http from './http'
import { formatClientAt } from '../utils/datetime'

export function submitBaselineLog(form, clientAtMs) {
  return http.post('/baseline/submit-log', {
    ...form,
    client_at: formatClientAt(clientAtMs),
  })
}

/** 拉取用户资料（含 baseline profile，供「我的」页展示） */
export function syncPull() {
  return http.get('/sync/pull')
}

export function fetchDailyTasks(taskDate, sessionId) {
  return http.get('/daily-tasks', {
    params: { task_date: taskDate, session_id: sessionId },
  })
}

export function submitEmaStep(type, payload, meta = {}) {
  return http.post('/ema/submission/submit', {
    type,
    payload,
    session_id: meta.sessionId || 1,
    task_date: meta.taskDate,
    client_at: formatClientAt(meta.clientAtMs),
  })
}

export function submitQuestionnaireLog(answers, answeredAtMs, sessionId, taskDate, durationSec) {
  const payload = { answers: answers || {} }
  if (durationSec != null) payload.durationSec = durationSec
  return submitEmaStep('questionnaire', payload, {
    clientAtMs: answeredAtMs,
    sessionId,
    taskDate,
  })
}

export function submitDiaryLog(text, length, writtenAtMs, sessionId, taskDate) {
  return submitEmaStep('diary', { text, length }, {
    clientAtMs: writtenAtMs,
    sessionId,
    taskDate,
  })
}

export function submitVoiceSkipLog(recordedAtMs, sessionId, taskDate) {
  return submitEmaStep('voice', { skip: true }, {
    clientAtMs: recordedAtMs,
    sessionId,
    taskDate,
  })
}

export function submitVideoSkipLog(recordedAtMs, sessionId, taskDate) {
  return submitEmaStep('video', { skip: true }, {
    clientAtMs: recordedAtMs,
    sessionId,
    taskDate,
  })
}

export function submitStepLog(steps, source, recordedAtMs, sessionId, taskDate, analytics) {
  const payload = { steps, source: source || 'manual' }
  if (analytics) payload.analytics = analytics
  return submitEmaStep('steps', payload, {
    clientAtMs: recordedAtMs,
    sessionId,
    taskDate,
  })
}

export async function uploadVoiceLog(file, durationSec, recordedAtMs, sessionId, taskDate) {
  const form = new FormData()
  form.append('file', file)
  form.append('skip', '0')
  form.append('duration_sec', String(durationSec))
  form.append('recorded_at', formatClientAt(recordedAtMs))
  form.append('session_id', String(sessionId || 1))
  form.append('task_date', taskDate || '')
  return http.post('/ema/voice/submit-log', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function uploadVideoLog(file, durationSec, recordedAtMs, sessionId, taskDate) {
  const form = new FormData()
  form.append('file', file)
  form.append('skip', '0')
  form.append('duration_sec', String(durationSec))
  form.append('recorded_at', formatClientAt(recordedAtMs))
  form.append('session_id', String(sessionId || 1))
  form.append('task_date', taskDate || '')
  return http.post('/ema/video/submit-log', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function saveRiskSnapshot(taskDate, sessionId, computedAtMs) {
  return http.post('/risk/snapshot', {
    task_date: taskDate,
    session_id: sessionId || 1,
    computed_at: formatClientAt(computedAtMs),
  })
}

export function fetchTrendsOverview(days = 7) {
  return http.get('/trends/overview', { params: { days } })
}

export function trackBehavior(module, action, extra, route) {
  const meta = JSON.parse(localStorage.getItem('ema_behavior_meta') || '{}') || {}
  return http.post('/behavior/track-log', {
    module,
    action,
    extra: extra || {},
    route: route || window.location.pathname,
    hour: new Date().getHours(),
    client_at: formatClientAt(Date.now()),
    behavior_meta: meta,
  })
}
