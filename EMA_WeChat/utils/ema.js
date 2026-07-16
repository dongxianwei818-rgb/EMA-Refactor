var C = require('./constants');

var KEY = {
  CONSENT: 'ema_consent',
  BASELINE: 'ema_baseline',
  SERVER_PROFILE: 'ema_server_profile',
  LOGIN_COUNT: 'ema_login_count',
  DAILY: 'ema_daily_tasks',
  VIDEO_DATES: 'ema_video_dates',
  SUBMISSIONS: 'ema_submissions',
  STEPS_HISTORY: 'ema_steps_history',
  STEPS_BASELINE: 'ema_steps_baseline',
  VIDEO_SKIPS: 'ema_video_skips',
  VOICE_SKIPS: 'ema_voice_skips',
  CHECKIN_DAY: 'ema_checkin_day',
};

var SKIP_MAX = 500;

function normalizeSkipList(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  return [];
}

function recordSkip(type, extra) {
  ensureCheckinSession();
  var key = type === 'video' ? KEY.VIDEO_SKIPS : KEY.VOICE_SKIPS;
  var at = Date.now();
  var list = normalizeSkipList(wx.getStorageSync(key));
  list.unshift({
    at: at,
    date: getTodayKey(),
    sessionId: getCurrentSessionId(),
    reason: (extra && extra.reason) || 'skip',
  });
  wx.setStorageSync(key, list.slice(0, SKIP_MAX));
  return at;
}

function getVideoSkips() {
  return normalizeSkipList(wx.getStorageSync(KEY.VIDEO_SKIPS));
}

function getVoiceSkips() {
  return normalizeSkipList(wx.getStorageSync(KEY.VOICE_SKIPS));
}

function getVideoSkipCount() {
  return getVideoSkips().length;
}

function getVoiceSkipCount() {
  return getVoiceSkips().length;
}

function getTodayKey() {
  var d = new Date();
  var m = d.getMonth() + 1;
  var day = d.getDate();
  return d.getFullYear() + '-' + (m < 10 ? '0' : '') + m + '-' + (day < 10 ? '0' : '') + day;
}

function hasConsent() {
  var server = getServerProfile();
  return server.has_consent === true;
}

function applyConsentFromServer(consentData) {
  var sp = getServerProfile();
  sp.has_consent = !!(consentData && consentData.has_consent);
  sp.consent_status = (consentData && consentData.status) || null;
  sp.consent_at = (consentData && consentData.at) || null;
  setServerProfile(sp);
  if (sp.has_consent && sp.consent_at) {
    acceptConsent(sp.consent_at);
  } else {
    revokeConsent();
  }
}

function hasBaseline() {
  return !!wx.getStorageSync(KEY.BASELINE);
}

function isResearchBound() {
  var server = wx.getStorageSync(KEY.SERVER_PROFILE) || {};
  if (server.research_id) return true;
  var profile = getProfile();
  return !!(profile.researchId || profile.research_id);
}

function setServerProfile(profile) {
  wx.setStorageSync(KEY.SERVER_PROFILE, profile || {});
}

function getServerProfile() {
  return wx.getStorageSync(KEY.SERVER_PROFILE) || {};
}

function clearBaseline() {
  wx.removeStorageSync(KEY.BASELINE);
  wx.removeStorageSync('ema_profile');
}

function isOnboardingComplete() {
  return hasConsent() && isResearchBound();
}

function getLoginCount() {
  return wx.getStorageSync(KEY.LOGIN_COUNT) || 0;
}

function incrementLoginCount() {
  var n = getLoginCount() + 1;
  wx.setStorageSync(KEY.LOGIN_COUNT, n);
  return n;
}

function setLoginCount(n) {
  wx.setStorageSync(KEY.LOGIN_COUNT, n || 0);
  return n || 0;
}

function getConsent() {
  var server = getServerProfile();
  if (server.consent_at) {
    return { at: server.consent_at };
  }
  return wx.getStorageSync(KEY.CONSENT) || null;
}

function acceptConsent(at) {
  wx.setStorageSync(KEY.CONSENT, { at: at || Date.now() });
}

function revokeConsent() {
  wx.removeStorageSync(KEY.CONSENT);
}

function saveBaseline(data) {
  wx.setStorageSync(KEY.BASELINE, Object.assign({}, data, { at: Date.now() }));
  wx.setStorageSync('ema_profile', data);
}

function getProfile() {
  return wx.getStorageSync('ema_profile') || wx.getStorageSync(KEY.BASELINE) || {};
}

function dailyStore() {
  return wx.getStorageSync(KEY.DAILY) || {};
}

function getTodayTasks() {
  var store = dailyStore();
  var t = getTodayKey();
  return store[t] || { questionnaire: false, diary: false, voice: false, video: false, steps: false, videoSkipped: false, voiceSkipped: false };
}

function applyServerDailyTasks(data) {
  if (!data) return;
  var tasks = data.tasks;
  var taskDate = data.task_date;
  if (!tasks || !taskDate) return;
  var defaults = {
    questionnaire: false,
    diary: false,
    voice: false,
    video: false,
    steps: false,
    videoSkipped: false,
    voiceSkipped: false,
  };
  var store = dailyStore();
  store[taskDate] = Object.assign({}, defaults, store[taskDate] || {}, tasks);
  wx.setStorageSync(KEY.DAILY, store);
}

function applyDailyTasksResponse(data) {
  if (!data) return;
  if (data.daily_tasks && typeof data.daily_tasks === 'object') {
    var store = dailyStore();
    Object.keys(data.daily_tasks).forEach(function (dateKey) {
      store[dateKey] = data.daily_tasks[dateKey];
    });
    wx.setStorageSync(KEY.DAILY, store);
    return;
  }
  applyServerDailyTasks(data);
}

function resetTodayTasks() {
  var store = dailyStore();
  store[getTodayKey()] = {
    questionnaire: false,
    diary: false,
    voice: false,
    video: false,
    steps: false,
    videoSkipped: false,
    voiceSkipped: false,
  };
  wx.setStorageSync(KEY.DAILY, store);
}

function getCheckinDayState() {
  var state = wx.getStorageSync(KEY.CHECKIN_DAY);
  var today = getTodayKey();
  if (!state || state.date !== today) {
    return { date: today, sessionId: 1, sessions: [] };
  }
  return state;
}

function saveCheckinDayState(state) {
  wx.setStorageSync(KEY.CHECKIN_DAY, state);
}

function getCurrentSessionId() {
  return getCheckinDayState().sessionId;
}

function ensureCheckinSession() {
  var state = getCheckinDayState();
  var found = false;
  for (var i = 0; i < state.sessions.length; i++) {
    if (state.sessions[i].id === state.sessionId) {
      found = true;
      break;
    }
  }
  if (!found) {
    var startedAt = Date.now();
    state.sessions.push({ id: state.sessionId, startedAt: startedAt, completedAt: null });
    saveCheckinDayState(state);
    require("./checkin").notifySessionStarted(state.sessionId, startedAt);
  }
  return state.sessionId;
}

function completeCurrentSession() {
  var state = getCheckinDayState();
  var session = null;
  for (var i = 0; i < state.sessions.length; i++) {
    if (state.sessions[i].id === state.sessionId) {
      session = state.sessions[i];
      break;
    }
  }
  if (!session) {
    session = { id: state.sessionId, startedAt: Date.now(), completedAt: null };
    state.sessions.push(session);
  }
  if (!session.completedAt) {
    session.completedAt = Date.now();
    saveCheckinDayState(state);
    require("./checkin").notifySessionCompleted(state.sessionId, session.completedAt);
  }
  return session;
}

function maybeCompleteSession() {
  if (!isTodayCheckinComplete()) return;
  var state = getCheckinDayState();
  var session = null;
  for (var i = 0; i < state.sessions.length; i++) {
    if (state.sessions[i].id === state.sessionId) {
      session = state.sessions[i];
      break;
    }
  }
  if (session && session.completedAt) return;
  session = completeCurrentSession();
  var tracker = require('./tracker');
  tracker.trackEvent('checkin', 'session_complete', {
    sessionId: session.id,
    date: getTodayKey(),
  });
}

function isTodayCheckinComplete() {
  var progress = getTaskProgress();
  return progress.done >= progress.total;
}

function startRecheckin() {
  var state = getCheckinDayState();
  if (isTodayCheckinComplete()) completeCurrentSession();
  var startedAt = Date.now();
  state.sessionId += 1;
  state.sessions.push({ id: state.sessionId, startedAt: startedAt, completedAt: null });
  saveCheckinDayState(state);
  resetTodayTasks();
  require("./checkin").notifySessionStarted(state.sessionId, startedAt);
  return state.sessionId;
}

function getTodayCheckinSessions() {
  return getCheckinDayState().sessions;
}

function markTaskDone(task) {
  ensureCheckinSession();
  var store = dailyStore();
  var t = getTodayKey();
  var tasks = Object.assign({}, getTodayTasks());
  tasks[task] = true;
  store[t] = tasks;
  wx.setStorageSync(KEY.DAILY, store);
  maybeCompleteSession();
  return tasks;
}

function markVideoSkipped(extra) {
  var tasks = markTaskDone('video');
  tasks.videoSkipped = true;
  var store = dailyStore();
  store[getTodayKey()] = tasks;
  wx.setStorageSync(KEY.DAILY, store);
  var at = recordSkip('video', extra);
  saveSubmission('video', { skip: true, reason: (extra && extra.reason) || 'skip' }, { at: at });
}

function markVoiceSkipped(extra) {
  var tasks = markTaskDone('voice');
  tasks.voiceSkipped = true;
  var store = dailyStore();
  store[getTodayKey()] = tasks;
  wx.setStorageSync(KEY.DAILY, store);
  var at = recordSkip('voice', extra);
  saveSubmission('voice', { skip: true, reason: (extra && extra.reason) || 'skip' }, { at: at });
}

function saveSubmission(type, payload, meta) {
  ensureCheckinSession();
  meta = meta || {};
  var list = wx.getStorageSync(KEY.SUBMISSIONS) || [];
  list.unshift({
    type: type,
    payload: payload || {},
    date: meta.date || getTodayKey(),
    at: meta.at || Date.now(),
    sessionId: meta.sessionId != null ? meta.sessionId : getCurrentSessionId(),
  });
  wx.setStorageSync(KEY.SUBMISSIONS, list.slice(0, 300));
}

function getSubmissions() {
  return wx.getStorageSync(KEY.SUBMISSIONS) || [];
}

function getLastSubmissionAt(type) {
  var list = getSubmissions();
  for (var i = 0; i < list.length; i++) {
    if (list[i].type === type && list[i].at) return list[i].at;
  }
  return null;
}

var MS_PER_DAY = 24 * 60 * 60 * 1000;

function getRecordingIntervalStatus(type) {
  var intervalDays = type === 'voice' ? C.VOICE_INTERVAL_DAYS : C.VIDEO_INTERVAL_DAYS;
  var lastAt = getLastSubmissionAt(type);
  if (!lastAt) {
    return { due: true, intervalDays: intervalDays, daysSince: null, daysRemaining: 0, lastAt: null };
  }
  var elapsedDays = (Date.now() - lastAt) / MS_PER_DAY;
  var due = elapsedDays >= intervalDays;
  var daysRemaining = due ? 0 : Math.ceil(intervalDays - elapsedDays);
  return {
    due: due,
    intervalDays: intervalDays,
    daysSince: Math.floor(elapsedDays),
    daysRemaining: daysRemaining,
    lastAt: lastAt,
  };
}

function isRecordingDue(type) {
  return getRecordingIntervalStatus(type).due;
}

function saveStepsHistory(steps) {
  var hist = wx.getStorageSync(KEY.STEPS_HISTORY) || [];
  var today = getTodayKey();
  var filtered = hist.filter(function (h) { return h.date !== today; });
  filtered.unshift({ date: today, steps: steps, at: Date.now() });
  wx.setStorageSync(KEY.STEPS_HISTORY, filtered.slice(0, 90));
  if (!wx.getStorageSync(KEY.STEPS_BASELINE) && filtered.length >= 3) {
    var sum = 0;
    for (var i = 0; i < Math.min(7, filtered.length); i++) sum += filtered[i].steps;
    wx.setStorageSync(KEY.STEPS_BASELINE, Math.round(sum / Math.min(7, filtered.length)));
  }
}

function getStepsAnalytics() {
  var hist = wx.getStorageSync(KEY.STEPS_HISTORY) || [];
  var baseline = wx.getStorageSync(KEY.STEPS_BASELINE) || 0;
  var today = hist[0] ? hist[0].steps : 0;
  var sum7 = 0;
  var count7 = Math.min(7, hist.length);
  for (var i = 0; i < count7; i++) sum7 += hist[i].steps;
  var avg7 = count7 ? Math.round(sum7 / count7) : 0;
  var lowDays = 0;
  var threshold = baseline ? baseline * 0.4 : 2000;
  for (var j = 0; j < hist.length && j < 14; j++) {
    if (hist[j].steps < threshold) lowDays++;
    else break;
  }
  var deviation = baseline && today ? Math.round(((today - baseline) / baseline) * 100) : 0;
  return { today: today, avg7: avg7, baseline: baseline, lowDays: lowDays, deviation: deviation, hist: hist };
}

function getVideoCountThisWeek() {
  var dates = wx.getStorageSync(KEY.VIDEO_DATES) || [];
  var now = new Date();
  var start = new Date(now);
  start.setDate(now.getDate() - now.getDay());
  start.setHours(0, 0, 0, 0);
  return dates.filter(function (ts) { return ts >= start.getTime(); }).length;
}

function markVideoDone() {
  var dates = wx.getStorageSync(KEY.VIDEO_DATES) || [];
  dates.push(Date.now());
  wx.setStorageSync(KEY.VIDEO_DATES, dates);
}

function shouldShowVoiceTask() {
  var tasks = getTodayTasks();
  return !tasks.voice && !tasks.voiceSkipped;
}

function shouldShowVideoTask() {
  var tasks = getTodayTasks();
  return !tasks.video && !tasks.videoSkipped;
}

var TASK_ORDER = ['questionnaire', 'diary', 'voice', 'video', 'steps'];
var ROUTES = {
  questionnaire: '/pages/ema/questionnaire/index',
  diary: '/pages/ema/diary/index',
  voice: '/pages/ema/voice/index',
  video: '/pages/ema/video/index',
  steps: '/pages/ema/steps/index',
};

function getTaskRoute(taskKey) {
  return ROUTES[taskKey] || null;
}

function getNextTaskRoute() {
  var tasks = getTodayTasks();
  for (var i = 0; i < TASK_ORDER.length; i++) {
    var task = TASK_ORDER[i];
    if (tasks[task]) continue;
    if (task === 'voice' && !shouldShowVoiceTask()) continue;
    if (task === 'video' && !shouldShowVideoTask()) continue;
    return ROUTES[task];
  }
  return null;
}

function getMissedDays() {
  var store = dailyStore();
  var missed = 0;
  for (var i = 1; i <= 14; i++) {
    var d = new Date();
    d.setDate(d.getDate() - i);
    var k = getTodayKeyFromDate(d);
    var t = store[k];
    if (!t || !t.questionnaire) missed++;
    else break;
  }
  return missed;
}

function getTodayKeyFromDate(d) {
  var m = d.getMonth() + 1;
  var day = d.getDate();
  return d.getFullYear() + '-' + (m < 10 ? '0' : '') + m + '-' + (day < 10 ? '0' : '') + day;
}

function getTaskProgress() {
  var tasks = getTodayTasks();
  var done = 0;
  var total = TASK_ORDER.length;
  TASK_ORDER.forEach(function (t) {
    if (tasks[t]) done++;
    else if (t === 'voice' && !shouldShowVoiceTask()) done++;
    else if (t === 'video' && !shouldShowVideoTask()) done++;
  });
  return { done: done, total: total, tasks: tasks, percent: Math.round((done / total) * 100) };
}

module.exports = {
  getTodayKey: getTodayKey,
  hasConsent: hasConsent,
  getConsent: getConsent,
  hasBaseline: hasBaseline,
  isResearchBound: isResearchBound,
  setServerProfile: setServerProfile,
  getServerProfile: getServerProfile,
  clearBaseline: clearBaseline,
  isOnboardingComplete: isOnboardingComplete,
  getLoginCount: getLoginCount,
  incrementLoginCount: incrementLoginCount,
  setLoginCount: setLoginCount,
  acceptConsent: acceptConsent,
  revokeConsent: revokeConsent,
  applyConsentFromServer: applyConsentFromServer,
  saveBaseline: saveBaseline,
  getProfile: getProfile,
  getTodayTasks: getTodayTasks,
  applyServerDailyTasks: applyServerDailyTasks,
  applyDailyTasksResponse: applyDailyTasksResponse,
  resetTodayTasks: resetTodayTasks,
  getCurrentSessionId: getCurrentSessionId,
  ensureCheckinSession: ensureCheckinSession,
  completeCurrentSession: completeCurrentSession,
  isTodayCheckinComplete: isTodayCheckinComplete,
  startRecheckin: startRecheckin,
  getTodayCheckinSessions: getTodayCheckinSessions,
  markTaskDone: markTaskDone,
  markVideoSkipped: markVideoSkipped,
  markVoiceSkipped: markVoiceSkipped,
  getVideoSkips: getVideoSkips,
  getVoiceSkips: getVoiceSkips,
  getVideoSkipCount: getVideoSkipCount,
  getVoiceSkipCount: getVoiceSkipCount,
  saveSubmission: saveSubmission,
  getSubmissions: getSubmissions,
  getLastSubmissionAt: getLastSubmissionAt,
  getRecordingIntervalStatus: getRecordingIntervalStatus,
  isRecordingDue: isRecordingDue,
  saveStepsHistory: saveStepsHistory,
  getStepsAnalytics: getStepsAnalytics,
  getVideoCountThisWeek: getVideoCountThisWeek,
  markVideoDone: markVideoDone,
  shouldShowVoiceTask: shouldShowVoiceTask,
  shouldShowVideoTask: shouldShowVideoTask,
  getTaskRoute: getTaskRoute,
  getNextTaskRoute: getNextTaskRoute,
  getTaskProgress: getTaskProgress,
  getMissedDays: getMissedDays,
  TASK_ORDER: TASK_ORDER,
};
