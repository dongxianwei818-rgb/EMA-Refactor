var KEY = 'ema_behavior_logs';
var META_KEY = 'ema_behavior_meta';
var MAX = 800;
var pendingQueue = [];

function postBehaviorEvent(entry) {
  var C = require('./constants');
  var sync = require('./sync');
  if (!C.API_BASE_URL) return;
  var token = sync.getToken();
  if (!token) {
    pendingQueue.push(entry);
    return;
  }
  var meta = wx.getStorageSync(META_KEY) || {};
  wx.request({
    url: C.API_BASE_URL.replace(/\/$/, '') + '/behavior/track-log',
    method: 'POST',
    header: {
      'content-type': 'application/json',
      Authorization: 'Bearer ' + token,
    },
    data: {
      module: entry.module,
      action: entry.action,
      extra: entry.extra || {},
      route: entry.route || '',
      hour: entry.hour,
      client_at: require('./datetime').formatClientAt(entry.at),
      behavior_meta: meta,
    },
    success: function (res) {
      var body = res.data || {};
      if (res.statusCode !== 200 || body.code !== 0) {
        console.warn('行为打点上报失败', body.message || res.statusCode);
      }
    },
    fail: function (err) {
      console.warn('行为打点上报失败', err);
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

function trackEvent(module, action, extra) {
  var pages = getCurrentPages();
  var page = pages[pages.length - 1];
  var entry = {
    module: module,
    action: action,
    extra: extra || {},
    route: page ? page.route : '',
    hour: new Date().getHours(),
    at: Date.now(),
  };
  var logs = wx.getStorageSync(KEY) || [];
  logs.unshift(entry);
  wx.setStorageSync(KEY, logs.slice(0, MAX));
  updateMeta(module, action, extra);
  postBehaviorEvent(entry);
  return entry;
}

function updateMeta(module, action, extra) {
  var meta = wx.getStorageSync(META_KEY) || {
    openCount: 0,
    checkinTimes: [],
    diaryWordCounts: [],
    voiceDurations: [],
    videoDurations: [],
    taskDurations: [],
    videoSkips: 0,
    voiceSkips: 0,
  };
  if (action === 'app_launch' || action === 'view' && module === 'app') meta.openCount++;
  if (action === 'submit' && module === 'questionnaire') {
    meta.checkinTimes.push({
      at: Date.now(),
      hour: new Date().getHours(),
      sessionId: (extra && extra.sessionId) || 1,
    });
  }
  if (action === 'session_complete' && module === 'checkin') {
    meta.checkinSessions = meta.checkinSessions || [];
    meta.checkinSessions.push({
      at: Date.now(),
      sessionId: extra && extra.sessionId,
      date: extra && extra.date,
    });
  }
  if (action === 'recheckin_start' && module === 'home') {
    meta.recheckinCount = (meta.recheckinCount || 0) + 1;
  }
  if (action === 'submit' && module === 'diary' && extra && extra.length) {
    meta.diaryWordCounts.push(extra.length);
  }
  if (action === 'submit' && module === 'voice' && extra && extra.duration) {
    meta.voiceDurations.push(extra.duration);
  }
  if (action === 'submit' && module === 'video' && extra && extra.duration) {
    meta.videoDurations = meta.videoDurations || [];
    meta.videoDurations.push(extra.duration);
  }
  if (action === 'task_duration' && extra) meta.taskDurations.push(extra);
  wx.setStorageSync(META_KEY, meta);
}

function startTaskTimer(pageRoute) {
  wx.setStorageSync('ema_task_timer', { route: pageRoute, start: Date.now() });
}

function endTaskTimer(module) {
  var t = wx.getStorageSync('ema_task_timer');
  if (t && t.start) {
    var ms = Date.now() - t.start;
    trackEvent(module, 'task_duration', { ms: ms, route: t.route });
    wx.removeStorageSync('ema_task_timer');
    return ms;
  }
  return 0;
}

function getBehaviorStats() {
  var logs = wx.getStorageSync(KEY) || [];
  var meta = wx.getStorageSync(META_KEY) || {};
  var byModule = {};
  logs.forEach(function (l) {
    byModule[l.module] = (byModule[l.module] || 0) + 1;
  });
  var ema = require('./ema');
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
    checkinHours: (meta.checkinTimes || []).slice(0, 7).map(function (c) { return c.hour; }),
    todaySessions: ema.getTodayCheckinSessions().length,
    recheckinCount: meta.recheckinCount || 0,
  };
}

function avg(arr) {
  if (!arr || !arr.length) return 0;
  var s = 0;
  for (var i = 0; i < arr.length; i++) s += arr[i];
  return Math.round(s / arr.length);
}

function getBehaviorMeta() {
  return wx.getStorageSync(META_KEY) || {};
}

function getBehaviorLogs() {
  return wx.getStorageSync(KEY) || [];
}

module.exports = {
  trackEvent: trackEvent,
  flushPendingBehavior: flushPendingBehavior,
  startTaskTimer: startTaskTimer,
  endTaskTimer: endTaskTimer,
  getBehaviorStats: getBehaviorStats,
  getBehaviorMeta: getBehaviorMeta,
  getBehaviorLogs: getBehaviorLogs,
};
