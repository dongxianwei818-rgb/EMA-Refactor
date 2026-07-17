/**
 * 会话内存仓：业务数据权威来源为后台接口，登录后 hydrate 写入此处。
 * localStorage 仅保留登录凭证与少量 UI 偏好（见 clearLegacyBusinessStorage）。
 */

const state = {
  baseline: null,
  dailyTasks: {},
  submissions: [],
  checkinDay: null,
  stepsHistory: [],
  stepsBaseline: 0,
  videoSkips: [],
  voiceSkips: [],
  videoDates: [],
  behaviorMeta: {},
  behaviorLogs: [],
  serverProfile: {},
  consent: null,
}

export function getStore() {
  return state
}

export function resetStore() {
  state.baseline = null
  state.dailyTasks = {}
  state.submissions = []
  state.checkinDay = null
  state.stepsHistory = []
  state.stepsBaseline = 0
  state.videoSkips = []
  state.voiceSkips = []
  state.videoDates = []
  state.behaviorMeta = {}
  state.behaviorLogs = []
  state.serverProfile = {}
  state.consent = null
}

/** 登录凭证以外的历史业务 localStorage 键，换端后不再依赖 */
export const LEGACY_BUSINESS_KEYS = [
  'ema_baseline',
  'ema_profile',
  'ema_consent',
  'ema_server_profile',
  'ema_daily_tasks',
  'ema_checkin_day',
  'ema_submissions',
  'ema_steps_history',
  'ema_steps_baseline',
  'ema_video_skips',
  'ema_voice_skips',
  'ema_video_dates',
  'ema_behavior_logs',
  'ema_behavior_meta',
  'ema_task_timer',
]

export function clearLegacyBusinessStorage() {
  LEGACY_BUSINESS_KEYS.forEach((key) => {
    try {
      localStorage.removeItem(key)
    } catch {
      /* ignore */
    }
  })
}

let lastHydratedAt = 0

export function getLastHydratedAt() {
  return lastHydratedAt
}

export function markHydrated() {
  lastHydratedAt = Date.now()
}

export function invalidateHydrateCache() {
  lastHydratedAt = 0
}
