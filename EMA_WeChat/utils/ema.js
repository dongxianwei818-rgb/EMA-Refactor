/**
 * EMA 会话状态：业务数据保存在内存（sessionStore），由 sync/pull 等接口填充。
 * Storage 仅保留登录凭证；换端登录后以服务端数据为准。
 */
var C = require("./constants");
var sessionStore = require("./sessionStore");

var SKIP_MAX = 500;
var MS_PER_DAY = 24 * 60 * 60 * 1000;
var TASK_ORDER = ["questionnaire", "diary", "voice", "video", "steps"];
var ROUTES = {
  questionnaire: "/pages/ema/questionnaire/index",
  diary: "/pages/ema/diary/index",
  voice: "/pages/ema/voice/index",
  video: "/pages/ema/video/index",
  steps: "/pages/ema/steps/index",
};

function emptyTasks() {
  return {
    questionnaire: false,
    diary: false,
    voice: false,
    video: false,
    steps: false,
    videoSkipped: false,
    voiceSkipped: false,
  };
}

function getStore() {
  return sessionStore.getStore();
}

function normalizeSkipList(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  return [];
}

function getTodayKey(d) {
  d = d || new Date();
  var m = d.getMonth() + 1;
  var day = d.getDate();
  return (
    d.getFullYear() +
    "-" +
    (m < 10 ? "0" : "") +
    m +
    "-" +
    (day < 10 ? "0" : "") +
    day
  );
}

function getTodayKeyFromDate(d) {
  return getTodayKey(d);
}

function hasConsent() {
  var server = getServerProfile();
  if (typeof server.has_consent === "boolean") return server.has_consent;
  var local = getStore().consent;
  return !!(local && local.at);
}

function getConsent() {
  var server = getServerProfile();
  if (server.consent_at) return { at: server.consent_at };
  return getStore().consent || null;
}

function acceptConsent(at) {
  getStore().consent = { at: at || Date.now() };
}

function revokeConsent() {
  getStore().consent = null;
}

function applyConsentFromServer(consentData) {
  var sp = getServerProfile();
  sp.has_consent = !!(consentData && consentData.has_consent);
  sp.consent_status = (consentData && consentData.status) || null;
  sp.consent_at = (consentData && consentData.at) || null;
  setServerProfile(sp);
  if (sp.has_consent && sp.consent_at) {
    acceptConsent(sp.consent_at);
  } else if (!sp.has_consent) {
    revokeConsent();
  }
}

function setServerProfile(profile) {
  getStore().serverProfile = profile || {};
}

function getServerProfile() {
  return getStore().serverProfile || {};
}

function saveBaseline(data) {
  var payload = Object.assign({}, data, { at: (data && data.at) || Date.now() });
  if (payload.research_id && !payload.researchId) {
    payload.researchId = payload.research_id;
  }
  getStore().baseline = payload;
}

function getProfile() {
  return getStore().baseline || {};
}

function clearBaseline() {
  getStore().baseline = null;
}

function hasBaseline() {
  var p = getProfile();
  return !!(p && (p.researchId || p.research_id || p.age != null));
}

function isResearchBound() {
  var server = getServerProfile();
  if (server.research_id || server.has_baseline) return true;
  var profile = getProfile();
  return !!(profile.researchId || profile.research_id);
}

function isOnboardingComplete() {
  return hasConsent() && isResearchBound();
}

function getLoginCount() {
  return getStore().loginCount || 0;
}

function incrementLoginCount() {
  var n = getLoginCount() + 1;
  getStore().loginCount = n;
  return n;
}

function setLoginCount(n) {
  getStore().loginCount = n || 0;
  return n || 0;
}

function dailyStore() {
  return getStore().dailyTasks || {};
}

function saveDailyStore(store) {
  getStore().dailyTasks = store;
}

function getTodayTasks() {
  var store = dailyStore();
  var t = getTodayKey();
  return store[t] || emptyTasks();
}

function applyServerDailyTasks(data) {
  if (!data) return;
  var tasks = data.tasks;
  var taskDate = data.task_date;
  if (!tasks || !taskDate) return;
  var store = Object.assign({}, dailyStore());
  store[taskDate] = Object.assign({}, emptyTasks(), store[taskDate] || {}, tasks);
  saveDailyStore(store);
}

function applyDailyTasksResponse(data) {
  if (!data) return;
  if (data.daily_tasks && typeof data.daily_tasks === "object") {
    var store = Object.assign({}, dailyStore());
    Object.keys(data.daily_tasks).forEach(function (dateKey) {
      store[dateKey] = data.daily_tasks[dateKey];
    });
    saveDailyStore(store);
    return;
  }
  applyServerDailyTasks(data);
}

function resetTodayTasks() {
  var store = Object.assign({}, dailyStore());
  store[getTodayKey()] = emptyTasks();
  saveDailyStore(store);
}

function getCheckinDayState() {
  var today = getTodayKey();
  var state = getStore().checkinDay;
  if (!state || state.date !== today) {
    state = { date: today, sessionId: 1, sessions: [] };
    getStore().checkinDay = state;
  }
  if (!Array.isArray(state.sessions)) state.sessions = [];
  if (!state.sessionId || state.sessionId < 1) state.sessionId = 1;
  return state;
}

function saveCheckinDayState(state) {
  getStore().checkinDay = state;
}

function getCheckinDaySnapshot() {
  return getStore().checkinDay;
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
    state.sessions.push({
      id: state.sessionId,
      startedAt: startedAt,
      completedAt: null,
    });
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
    require("./checkin").notifySessionCompleted(
      state.sessionId,
      session.completedAt
    );
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
  require("./tracker").trackEvent("checkin", "session_complete", {
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
  state.sessions.push({
    id: state.sessionId,
    startedAt: startedAt,
    completedAt: null,
  });
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
  var store = Object.assign({}, dailyStore());
  var t = getTodayKey();
  var tasks = Object.assign({}, getTodayTasks());
  tasks[task] = true;
  store[t] = tasks;
  saveDailyStore(store);
  maybeCompleteSession();
  return tasks;
}

function recordSkip(type, extra) {
  ensureCheckinSession();
  var at = Date.now();
  var listKey = type === "video" ? "videoSkips" : "voiceSkips";
  var list = normalizeSkipList(getStore()[listKey]);
  list.unshift({
    at: at,
    date: getTodayKey(),
    sessionId: getCurrentSessionId(),
    reason: (extra && extra.reason) || "skip",
  });
  getStore()[listKey] = list.slice(0, SKIP_MAX);
  return at;
}

function getVideoSkips() {
  return normalizeSkipList(getStore().videoSkips);
}

function getVoiceSkips() {
  return normalizeSkipList(getStore().voiceSkips);
}

function getVideoSkipCount() {
  return getVideoSkips().length;
}

function getVoiceSkipCount() {
  return getVoiceSkips().length;
}

function markVideoSkipped(extra) {
  var tasks = markTaskDone("video");
  tasks.videoSkipped = true;
  var store = Object.assign({}, dailyStore());
  store[getTodayKey()] = tasks;
  saveDailyStore(store);
  var at = recordSkip("video", extra);
  saveSubmission(
    "video",
    { skip: true, reason: (extra && extra.reason) || "skip" },
    { at: at }
  );
}

function markVoiceSkipped(extra) {
  var tasks = markTaskDone("voice");
  tasks.voiceSkipped = true;
  var store = Object.assign({}, dailyStore());
  store[getTodayKey()] = tasks;
  saveDailyStore(store);
  var at = recordSkip("voice", extra);
  saveSubmission(
    "voice",
    { skip: true, reason: (extra && extra.reason) || "skip" },
    { at: at }
  );
}

function saveSubmission(type, payload, meta) {
  ensureCheckinSession();
  meta = meta || {};
  var list = getStore().submissions || [];
  list.unshift({
    type: type,
    payload: payload || {},
    date: meta.date || getTodayKey(),
    at: meta.at || Date.now(),
    sessionId: meta.sessionId != null ? meta.sessionId : getCurrentSessionId(),
  });
  getStore().submissions = list.slice(0, 300);
}

function getSubmissions() {
  return getStore().submissions || [];
}

function getLastSubmissionAt(type) {
  var list = getSubmissions();
  for (var i = 0; i < list.length; i++) {
    if (list[i].type === type && list[i].at) return list[i].at;
  }
  return null;
}

function getRecordingIntervalStatus(type) {
  var intervalDays =
    type === "voice" ? C.VOICE_INTERVAL_DAYS : C.VIDEO_INTERVAL_DAYS;
  var lastAt = getLastSubmissionAt(type);
  if (!lastAt) {
    return {
      due: true,
      intervalDays: intervalDays,
      daysSince: null,
      daysRemaining: 0,
      lastAt: null,
    };
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
  var hist = (getStore().stepsHistory || []).slice();
  var today = getTodayKey();
  var filtered = hist.filter(function (h) {
    return h.date !== today;
  });
  filtered.unshift({ date: today, steps: steps, at: Date.now() });
  getStore().stepsHistory = filtered.slice(0, 90);
  if (!getStore().stepsBaseline && filtered.length >= 3) {
    var sum = 0;
    var n = Math.min(7, filtered.length);
    for (var i = 0; i < n; i++) sum += filtered[i].steps;
    getStore().stepsBaseline = Math.round(sum / n);
  }
}

function getStepsAnalytics() {
  var hist = getStore().stepsHistory || [];
  var baseline = getStore().stepsBaseline || 0;
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
  var deviation =
    baseline && today ? Math.round(((today - baseline) / baseline) * 100) : 0;
  return {
    today: today,
    avg7: avg7,
    baseline: baseline,
    lowDays: lowDays,
    deviation: deviation,
    hist: hist,
  };
}

function getVideoCountThisWeek() {
  var dates = getStore().videoDates || [];
  var now = new Date();
  var start = new Date(now);
  start.setDate(now.getDate() - now.getDay());
  start.setHours(0, 0, 0, 0);
  var startTs = start.getTime();
  return dates.filter(function (ts) {
    var t = typeof ts === "number" ? ts : new Date(ts).getTime();
    return t >= startTs;
  }).length;
}

function markVideoDone() {
  var dates = (getStore().videoDates || []).slice();
  dates.push(Date.now());
  getStore().videoDates = dates;
}

function shouldShowVoiceTask() {
  var tasks = getTodayTasks();
  return !tasks.voice && !tasks.voiceSkipped;
}

function shouldShowVideoTask() {
  var tasks = getTodayTasks();
  return !tasks.video && !tasks.videoSkipped;
}

function getTaskRoute(taskKey) {
  return ROUTES[taskKey] || null;
}

function getNextTaskRoute() {
  var tasks = getTodayTasks();
  for (var i = 0; i < TASK_ORDER.length; i++) {
    var task = TASK_ORDER[i];
    if (tasks[task]) continue;
    if (task === "voice" && !shouldShowVoiceTask()) continue;
    if (task === "video" && !shouldShowVideoTask()) continue;
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

function getTaskProgress() {
  var tasks = getTodayTasks();
  var done = 0;
  var total = TASK_ORDER.length;
  TASK_ORDER.forEach(function (t) {
    if (tasks[t]) done++;
    else if (t === "voice" && !shouldShowVoiceTask()) done++;
    else if (t === "video" && !shouldShowVideoTask()) done++;
  });
  return {
    done: done,
    total: total,
    tasks: tasks,
    percent: Math.round((done / total) * 100),
  };
}

/** 将 sync/pull 返回写入内存会话仓 */
function applySyncPullPayload(data) {
  if (!data || typeof data !== "object") return;
  var store = getStore();

  if (data.baseline) {
    saveBaseline(
      Object.assign({}, data.baseline, {
        researchId:
          data.baseline.researchId ||
          data.baseline.research_id ||
          data.research_id ||
          "",
        at: data.baseline.at || Date.now(),
      })
    );
  } else if (data.research_id) {
    var local = getProfile() || {};
    if (!local.researchId && !local.research_id) {
      saveBaseline(
        Object.assign({}, local, {
          researchId: data.research_id,
          at: local.at || Date.now(),
        })
      );
    }
  }

  if (data.daily_tasks && typeof data.daily_tasks === "object") {
    applyDailyTasksResponse({ daily_tasks: data.daily_tasks });
  }

  if (data.checkin_day && typeof data.checkin_day === "object") {
    var today = getTodayKey();
    if (data.checkin_day.date === today || !data.checkin_day.date) {
      var incoming = {
        date: data.checkin_day.date || today,
        sessionId: Number(
          data.checkin_day.sessionId || data.checkin_day.session_id || 1
        ),
        sessions: Array.isArray(data.checkin_day.sessions)
          ? data.checkin_day.sessions.map(function (s) {
              return {
                id: Number(s.id),
                startedAt: s.startedAt || s.started_at || null,
                completedAt:
                  s.completedAt != null
                    ? s.completedAt
                    : s.completed_at != null
                      ? s.completed_at
                      : null,
              };
            })
          : [],
      };
      var localDay = store.checkinDay;
      if (localDay && localDay.date === incoming.date) {
        var byId = {};
        (localDay.sessions || [])
          .concat(incoming.sessions)
          .forEach(function (s) {
            if (!s || !s.id) return;
            var prev = byId[s.id];
            byId[s.id] = {
              id: s.id,
              startedAt: s.startedAt || (prev && prev.startedAt) || null,
              completedAt:
                s.completedAt != null
                  ? s.completedAt
                  : prev && prev.completedAt != null
                    ? prev.completedAt
                    : null,
            };
          });
        var sessions = Object.keys(byId)
          .map(function (k) {
            return byId[k];
          })
          .sort(function (a, b) {
            return a.id - b.id;
          });
        var maxId = Math.max(
          Number(localDay.sessionId) || 1,
          Number(incoming.sessionId) || 1,
          1
        );
        sessions.forEach(function (s) {
          if (s.id > maxId) maxId = s.id;
        });
        store.checkinDay = { date: today, sessionId: maxId, sessions: sessions };
      } else {
        store.checkinDay = incoming;
      }
    }
  }

  if (Array.isArray(data.submissions)) {
    store.submissions = data.submissions.map(function (s) {
      return {
        type: s.type,
        payload: s.payload || {},
        date: s.date,
        at: s.at || Date.now(),
        sessionId: s.sessionId != null ? s.sessionId : s.session_id || 1,
      };
    });
  }

  if (Array.isArray(data.steps_history)) {
    store.stepsHistory = data.steps_history;
  }
  if (data.steps_baseline != null) {
    store.stepsBaseline = data.steps_baseline;
  }
  if (Array.isArray(data.video_skips)) {
    store.videoSkips = data.video_skips;
  }
  if (Array.isArray(data.voice_skips)) {
    store.voiceSkips = data.voice_skips;
  }
  if (Array.isArray(data.video_dates)) {
    store.videoDates = data.video_dates;
  }

  require("./tracker").replaceBehaviorFromServer(
    data.behavior_meta,
    data.behavior_logs
  );
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
  applySyncPullPayload: applySyncPullPayload,
  resetTodayTasks: resetTodayTasks,
  getCurrentSessionId: getCurrentSessionId,
  getCheckinDaySnapshot: getCheckinDaySnapshot,
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
