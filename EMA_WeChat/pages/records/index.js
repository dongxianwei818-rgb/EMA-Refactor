var ema = require('../../utils/ema');
var tracker = require('../../utils/tracker');
var C = require('../../utils/constants');

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

function buildQuestionnaireAnswers(payload) {
  var answers = (payload && payload.answers) || {};
  var rows = [];
  (C.EMA_QUESTIONS || []).forEach(function (q) {
    var raw = answers[q.id];
    if (raw === undefined || raw === null || raw === '') return;
    var value =
      q.type === 'scale10' ? String(raw) + '/10' : String(raw);
    rows.push({ id: q.id, label: q.label, value: value });
  });
  return rows;
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
    var entry = {
      id: item.type + '_' + (item.at || 0),
      type: item.type,
      typeLabel: LABELS[item.type] || item.type,
      summary: buildItemSummary(item),
      timeLabel: formatTime(item.at),
      answerRows: [],
    };
    if (item.type === 'questionnaire') {
      entry.answerRows = buildQuestionnaireAnswers(item.payload || {});
    }
    g.items.push(entry);
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

function dedupeSubmissions(list) {
  // 同一会话同类型只保留一条（取最新 at），避免本地暂存与接口/同步因 client_at 毫秒差产生的重复
  var best = {};
  (list || []).forEach(function (item) {
    if (!item || !item.type) return;
    var key =
      item.type +
      "|" +
      (item.date || "") +
      "|" +
      (item.sessionId != null ? item.sessionId : 1);
    var prev = best[key];
    if (!prev || (item.at || 0) >= (prev.at || 0)) {
      best[key] = item;
    }
  });
  return Object.keys(best).map(function (k) {
    return best[k];
  });
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
  var merged = dedupeSubmissions(list);
  ema.getVoiceSkips().forEach(function (item) {
    var date = item.date || ema.getTodayKey();
    var sessionId = item.sessionId || 1;
    if (hasSkipRecord(merged, 'voice', date, sessionId)) return;
    // 同会话已有正式语音提交则不再补跳过占位
    var hasVoice = merged.some(function (s) {
      return (
        s.type === 'voice' &&
        s.date === date &&
        (s.sessionId || 1) === sessionId
      );
    });
    if (hasVoice) return;
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
    var hasVideo = merged.some(function (s) {
      return (
        s.type === 'video' &&
        s.date === date &&
        (s.sessionId || 1) === sessionId
      );
    });
    if (hasVideo) return;
    merged.push({
      type: 'video',
      payload: { skip: true, reason: item.reason || 'skip' },
      date: date,
      at: item.at || Date.now(),
      sessionId: sessionId,
    });
  });
  return dedupeSubmissions(merged);
}

Page({
  data: { sessions: [], totalCount: 0, expandedKey: '' },

  onShow: function () {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1 });
    }
    var that = this;
    var auth = require('../../utils/auth');
    var hydrate = require('../../utils/hydrate');
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }
    hydrate
      .hydrateFromServer()
      .catch(function (err) {
        console.warn('记录页 hydrate 失败', (err && err.message) || err);
      })
      .then(function () {
        tracker.trackEvent('records', 'view');
        var raw = mergeSkipRecords(ema.getSubmissions());
        var sessions = groupSubmissions(raw);
        var prevKey = that.data.expandedKey;
        var stillExists = sessions.some(function (s) {
          return s.key === prevKey;
        });
        that.setData({
          sessions: sessions,
          totalCount: raw.length,
          // 默认展开第一条；刷新后若原展开项仍在则保持
          expandedKey: stillExists
            ? prevKey
            : sessions.length
              ? sessions[0].key
              : '',
        });
      });
  },

  onToggleSession: function (e) {
    var key = e.currentTarget.dataset.key;
    if (!key) return;
    // 手风琴：展开当前，收起其他；再次点击当前则收起
    this.setData({
      expandedKey: this.data.expandedKey === key ? '' : key,
    });
  },
});
