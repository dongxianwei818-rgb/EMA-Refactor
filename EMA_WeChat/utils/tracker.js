var sessionStore = require("./sessionStore");

var MAX = 800;
var pendingQueue = [];
var taskTimer = null;

function getMeta() {
  return sessionStore.getStore().behaviorMeta || {};
}

function setMeta(meta) {
  sessionStore.getStore().behaviorMeta = meta || {};
}

function getLogs() {
  var logs = sessionStore.getStore().behaviorLogs;
  return Array.isArray(logs) ? logs : [];
}

function setLogs(logs) {
  sessionStore.getStore().behaviorLogs = logs || [];
}

function replaceBehaviorFromServer(meta, logs) {
  if (meta && typeof meta === "object") {
    setMeta(meta);
  }
  if (Array.isArray(logs)) {
    setLogs(logs.slice(0, MAX));
  }
}

function postBehaviorEvent(entry) {
  var C = require("./constants");
  var sync = require("./sync");
  if (!C.API_BASE_URL) return;
  var token = sync.getToken();
  if (!token) {
    pendingQueue.push(entry);
    return;
  }
  wx.request({
    url: C.API_BASE_URL.replace(/\/$/, "") + "/behavior/track-log",
    method: "POST",
    header: {
      "content-type": "application/json",
      Authorization: "Bearer " + token,
      "X-Client-Type": "wechat",
    },
    data: {
      module: entry.module,
      action: entry.action,
      extra: entry.extra || {},
      route: entry.route || "",
      hour: entry.hour,
      client_at: require("./datetime").formatClientAt(entry.at),
      behavior_meta: getMeta(),
    },
    success: function (res) {
      var body = res.data || {};
      if (res.statusCode !== 200 || body.code !== 0) {
        console.warn("行为打点上报失败", body.message || res.statusCode);
      }
    },
    fail: function (err) {
      console.warn("行为打点上报失败", err);
    },
  });
}

function flushPendingBehavior() {
  if (!pendingQueue.length) return;
  var queue = pendingQueue.slice();
  pendingQueue = [];
  queue.forEach(function (entry) {
    postBehaviorEvent(entry);
  });
}

function updateMeta(module, action, extra) {
  var meta = Object.assign(
    {
      openCount: 0,
      checkinTimes: [],
      diaryWordCounts: [],
      voiceDurations: [],
      videoDurations: [],
      taskDurations: [],
      videoSkips: 0,
      voiceSkips: 0,
    },
    getMeta()
  );
  if (action === "app_launch" || (action === "view" && module === "app")) {
    meta.openCount++;
  }
  if (action === "submit" && module === "questionnaire") {
    meta.checkinTimes = meta.checkinTimes || [];
    meta.checkinTimes.push({
      at: Date.now(),
      hour: new Date().getHours(),
      sessionId: (extra && extra.sessionId) || 1,
    });
  }
  if (action === "session_complete" && module === "checkin") {
    meta.checkinSessions = meta.checkinSessions || [];
    meta.checkinSessions.push({
      at: Date.now(),
      sessionId: extra && extra.sessionId,
      date: extra && extra.date,
    });
  }
  if (action === "recheckin_start" && module === "home") {
    meta.recheckinCount = (meta.recheckinCount || 0) + 1;
  }
  if (action === "submit" && module === "diary" && extra && extra.length) {
    meta.diaryWordCounts = meta.diaryWordCounts || [];
    meta.diaryWordCounts.push(extra.length);
  }
  if (action === "submit" && module === "voice" && extra && extra.duration) {
    meta.voiceDurations = meta.voiceDurations || [];
    meta.voiceDurations.push(extra.duration);
  }
  if (action === "submit" && module === "video" && extra && extra.duration) {
    meta.videoDurations = meta.videoDurations || [];
    meta.videoDurations.push(extra.duration);
  }
  if (action === "task_duration" && extra) {
    meta.taskDurations = meta.taskDurations || [];
    meta.taskDurations.push(extra);
  }
  setMeta(meta);
}

function trackEvent(module, action, extra) {
  var pages = getCurrentPages();
  var page = pages[pages.length - 1];
  var entry = {
    module: module,
    action: action,
    extra: extra || {},
    route: page ? page.route : "",
    hour: new Date().getHours(),
    at: Date.now(),
  };
  var logs = getLogs();
  logs.unshift(entry);
  setLogs(logs.slice(0, MAX));
  updateMeta(module, action, extra);
  postBehaviorEvent(entry);
  return entry;
}

function startTaskTimer(pageRoute) {
  taskTimer = { route: pageRoute, start: Date.now() };
}

function endTaskTimer(module) {
  if (taskTimer && taskTimer.start) {
    var ms = Date.now() - taskTimer.start;
    var route = taskTimer.route;
    taskTimer = null;
    trackEvent(module, "task_duration", { ms: ms, route: route });
    return ms;
  }
  return 0;
}

function avg(arr) {
  if (!arr || !arr.length) return 0;
  var s = 0;
  for (var i = 0; i < arr.length; i++) s += arr[i];
  return Math.round(s / arr.length);
}

function getBehaviorStats() {
  var logs = getLogs();
  var meta = getMeta();
  var byModule = {};
  logs.forEach(function (l) {
    byModule[l.module] = (byModule[l.module] || 0) + 1;
  });
  var ema = require("./ema");
  return {
    total: logs.length,
    byModule: byModule,
    openCount: meta.openCount || 0,
    avgDiaryWords: avg(meta.diaryWordCounts),
    avgVoiceSec: avg(meta.voiceDurations),
    avgVideoSec: avg(meta.videoDurations),
    videoSkips: ema.getVideoSkipCount(),
    voiceSkips: ema.getVoiceSkipCount(),
    videoSkipRecords: ema.getVideoSkips(),
    voiceSkipRecords: ema.getVoiceSkips(),
    missedDays: ema.getMissedDays(),
    checkinHours: (meta.checkinTimes || []).slice(0, 7).map(function (c) {
      return c.hour;
    }),
    todaySessions: ema.getTodayCheckinSessions().length,
    recheckinCount: meta.recheckinCount || 0,
  };
}

module.exports = {
  trackEvent: trackEvent,
  flushPendingBehavior: flushPendingBehavior,
  startTaskTimer: startTaskTimer,
  endTaskTimer: endTaskTimer,
  getBehaviorStats: getBehaviorStats,
  getBehaviorMeta: getMeta,
  getBehaviorLogs: getLogs,
  replaceBehaviorFromServer: replaceBehaviorFromServer,
};
