var ema = require('../../utils/ema');
var tracker = require('../../utils/tracker');

var LABELS = {
  questionnaire: 'EMA 问卷',
  diary: '文本日记',
  voice: '语音任务',
  video: '视频任务',
  steps: '运动步数',
};

var TYPE_ORDER = ['questionnaire', 'diary', 'voice', 'video', 'steps'];

function formatDateLabel(dateStr) {
  var parts = dateStr.split('-');
  if (parts.length !== 3) return dateStr;
  return parts[0] + '年' + Number(parts[1]) + '月' + Number(parts[2]) + '日';
}

function formatTime(ts) {
  if (!ts) return '';
  var d = new Date(ts);
  var h = d.getHours();
  var m = d.getMinutes();
  return (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m;
}

function buildItemSummary(item) {
  var p = item.payload || {};
  switch (item.type) {
    case 'diary':
      return p.text || '（无内容）';
    case 'steps':
      return '步数 ' + (p.steps != null ? p.steps : '--');
    case 'questionnaire':
      return '完成用时 ' + (p.durationSec != null ? p.durationSec : '--') + ' 秒';
    case 'voice':
      if (p.skip) return '语音跳过';
      return '录音时长 ' + (p.duration != null ? p.duration : '--') + ' 秒';
    case 'video':
      if (p.skip) return '视频跳过';
      return (
        '视频时长 ' +
        (p.duration != null ? p.duration : '--') +
        ' 秒' +
        (p.hideFace ? ' · 不露脸' : '')
      );
    default:
      return '已本地暂存，待同步服务端';
  }
}

function groupSubmissions(list) {
  var groups = {};
  list.forEach(function (item) {
    var sid = item.sessionId || 1;
    var key = item.date + '_' + sid;
    if (!groups[key]) {
      groups[key] = {
        key: key,
        date: item.date,
        dateLabel: formatDateLabel(item.date),
        sessionId: sid,
        startedAt: item.at,
        endedAt: item.at,
        items: [],
      };
    }
    var g = groups[key];
    if (item.at) {
      if (!g.startedAt || item.at < g.startedAt) g.startedAt = item.at;
      if (!g.endedAt || item.at > g.endedAt) g.endedAt = item.at;
    }
    g.items.push({
      id: item.type + '_' + (item.at || 0),
      type: item.type,
      typeLabel: LABELS[item.type] || item.type,
      summary: buildItemSummary(item),
      timeLabel: formatTime(item.at),
    });
  });

  var sessions = Object.keys(groups).map(function (k) {
    return groups[k];
  });
  sessions.sort(function (a, b) {
    if (a.date !== b.date) return a.date < b.date ? 1 : -1;
    return b.sessionId - a.sessionId;
  });

  sessions.forEach(function (s) {
    s.items.sort(function (a, b) {
      return TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type);
    });
    s.itemCount = s.items.length;
    s.timeRange =
      s.startedAt && s.endedAt && s.startedAt !== s.endedAt
        ? formatTime(s.startedAt) + ' – ' + formatTime(s.endedAt)
        : formatTime(s.startedAt || s.endedAt);
  });

  return sessions;
}

function hasSkipRecord(list, type, date, sessionId) {
  for (var i = 0; i < list.length; i++) {
    var item = list[i];
    if (
      item.type === type &&
      item.date === date &&
      (item.sessionId || 1) === sessionId &&
      item.payload &&
      item.payload.skip
    ) {
      return true;
    }
  }
  return false;
}

function mergeSkipRecords(list) {
  var merged = list.slice();
  ema.getVoiceSkips().forEach(function (item) {
    var date = item.date || ema.getTodayKey();
    var sessionId = item.sessionId || 1;
    if (hasSkipRecord(merged, 'voice', date, sessionId)) return;
    merged.push({
      type: 'voice',
      payload: { skip: true, reason: item.reason || 'skip' },
      date: date,
      at: item.at || Date.now(),
      sessionId: sessionId,
    });
  });
  ema.getVideoSkips().forEach(function (item) {
    var date = item.date || ema.getTodayKey();
    var sessionId = item.sessionId || 1;
    if (hasSkipRecord(merged, 'video', date, sessionId)) return;
    merged.push({
      type: 'video',
      payload: { skip: true, reason: item.reason || 'skip' },
      date: date,
      at: item.at || Date.now(),
      sessionId: sessionId,
    });
  });
  return merged;
}

Page({
  data: { sessions: [], totalCount: 0 },

  onShow: function () {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1 });
    }
    tracker.trackEvent('records', 'view');
    var raw = mergeSkipRecords(ema.getSubmissions());
    var sessions = groupSubmissions(raw);
    this.setData({
      sessions: sessions,
      totalCount: raw.length,
    });
  },
});
