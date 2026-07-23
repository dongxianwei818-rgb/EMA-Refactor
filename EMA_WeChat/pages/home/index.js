var ema = require('../../utils/ema');
var tracker = require('../../utils/tracker');
var hydrate = require('../../utils/hydrate');
var auth = require('../../utils/auth');
var C = require('../../utils/constants');

var META = [
  { key: 'questionnaire', name: '每日 EMA', desc: '8项·0-10分·约30-60秒' },
  { key: 'diary', name: '文本日记', desc: '30-100字' },
  { key: 'voice', name: '语音任务', desc: '每' + C.VOICE_INTERVAL_DAYS + '天1次·5-60秒' },
  { key: 'video', name: '视频任务', desc: '每' + C.VIDEO_INTERVAL_DAYS + '天1次·5-60秒' },
  { key: 'steps', name: '运动步数', desc: '个体化基线对比' },
];

Page({
  data: { today: '', progress: {}, taskList: [], allDone: false, hasConsent: false, hasBaseline: false },

  onShow: function () {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 0 });
    }
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }
    var that = this;
    hydrate
      .hydrateFromServer()
      .catch(function (err) {
        console.warn('首页 hydrate 失败', (err && err.message) || err);
      })
      .then(function () {
        if (!ema.hasConsent()) {
          wx.redirectTo({ url: '/pages/onboarding/consent/index' });
          return;
        }
        if (!ema.isResearchBound()) {
          wx.redirectTo({ url: '/pages/onboarding/baseline/index' });
          return;
        }
        tracker.trackEvent('home', 'view');
        that.refresh();
      });
  },

  refresh: function () {
    var d = new Date();
    var progress = ema.getTaskProgress();
    var tasks = ema.getTodayTasks();
    var taskList = META.map(function (item) {
      var skip = false;
      if (item.key === 'voice' && tasks.voiceSkipped) skip = true;
      if (item.key === 'video' && tasks.videoSkipped) skip = true;
      var done = !!tasks[item.key] && !skip;
      return {
        key: item.key,
        name: item.name,
        desc: item.desc,
        done: done,
        skip: skip,
        canTap: !done && !skip,
      };
    });
    this.setData({
      today: d.getFullYear() + '年' + (d.getMonth() + 1) + '月' + d.getDate() + '日',
      progress: progress,
      taskList: taskList,
      allDone: progress.done >= progress.total,
      sessionCount: ema.getTodayCheckinSessions().length,
      checkinComplete: ema.isTodayCheckinComplete(),
      hasConsent: ema.hasConsent(),
      hasBaseline: ema.isResearchBound(),
    });
  },

  /** 打卡前：已完成知情同意 + 基线测评（各仅一次） */
  ensureReadyForCheckin: function () {
    if (!ema.hasConsent()) {
      wx.redirectTo({ url: '/pages/onboarding/consent/index' });
      return false;
    }
    if (!ema.isResearchBound()) {
      wx.redirectTo({ url: '/pages/onboarding/baseline/index' });
      return false;
    }
    return true;
  },

  startFlow: function () {
    if (!this.ensureReadyForCheckin()) return;
    if (ema.isTodayCheckinComplete()) {
      var that = this;
      wx.showModal({
        title: '提示',
        content: '已经完成今日打卡，是否重新打卡？',
        confirmText: '重新打卡',
        cancelText: '取消',
        success: function (res) {
          if (!res.confirm) return;
          var sessionId = ema.startRecheckin();
          tracker.trackEvent('home', 'recheckin_start', { sessionId: sessionId });
          that.navigateToNextTask(true, sessionId);
        },
      });
      return;
    }
    this.navigateToNextTask(false);
  },

  navigateToNextTask: function (isRecheckin, sessionId) {
    var sid = sessionId || ema.ensureCheckinSession();
    tracker.trackEvent('home', 'start_flow', { sessionId: sid, recheckin: !!isRecheckin });
    var next = ema.getNextTaskRoute();
    if (next) wx.navigateTo({ url: next });
    else wx.showToast({ title: '今日已完成', icon: 'success' });
  },

  onTaskTap: function (e) {
    var key = e.currentTarget.dataset.key;
    var canTap = e.currentTarget.dataset.canTap;
    if (canTap !== true && canTap !== 'true') return;
    if (!this.ensureReadyForCheckin()) return;
    var route = ema.getTaskRoute(key);
    if (!route) return;
    tracker.trackEvent('home', 'start_task', { task: key });
    wx.navigateTo({ url: route });
  },
});
