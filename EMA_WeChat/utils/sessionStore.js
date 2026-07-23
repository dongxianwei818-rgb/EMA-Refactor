/**
 * 会话内存仓：业务数据权威来源为后台接口，登录后 hydrate 写入此处。
 * Storage 仅保留登录凭证（token / user_id / user_name）。
 */

var state = {
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
  loginCount: 0,
};

var lastHydratedAt = 0;

function getStore() {
  return state;
}

function resetStore() {
  state.baseline = null;
  state.dailyTasks = {};
  state.submissions = [];
  state.checkinDay = null;
  state.stepsHistory = [];
  state.stepsBaseline = 0;
  state.videoSkips = [];
  state.voiceSkips = [];
  state.videoDates = [];
  state.behaviorMeta = {};
  state.behaviorLogs = [];
  state.serverProfile = {};
  state.consent = null;
  state.loginCount = 0;
}

/** 登录凭证以外的历史业务 Storage 键，不再依赖 */
var LEGACY_BUSINESS_KEYS = [
  "ema_baseline",
  "ema_profile",
  "ema_consent",
  "ema_server_profile",
  "ema_login_count",
  "ema_daily_tasks",
  "ema_checkin_day",
  "ema_submissions",
  "ema_steps_history",
  "ema_steps_baseline",
  "ema_video_skips",
  "ema_voice_skips",
  "ema_video_dates",
  "ema_behavior_logs",
  "ema_behavior_meta",
  "ema_task_timer",
];

function clearLegacyBusinessStorage() {
  LEGACY_BUSINESS_KEYS.forEach(function (key) {
    try {
      wx.removeStorageSync(key);
    } catch (e) {
      /* ignore */
    }
  });
}

function getLastHydratedAt() {
  return lastHydratedAt;
}

function markHydrated() {
  lastHydratedAt = Date.now();
}

function invalidateHydrateCache() {
  lastHydratedAt = 0;
}

module.exports = {
  getStore: getStore,
  resetStore: resetStore,
  LEGACY_BUSINESS_KEYS: LEGACY_BUSINESS_KEYS,
  clearLegacyBusinessStorage: clearLegacyBusinessStorage,
  getLastHydratedAt: getLastHydratedAt,
  markHydrated: markHydrated,
  invalidateHydrateCache: invalidateHydrateCache,
};
