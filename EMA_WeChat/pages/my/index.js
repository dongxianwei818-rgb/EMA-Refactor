var ema = require("../../utils/ema");
var consentApi = require("../../utils/consent");
var profileUtil = require("../../utils/profile");
var tracker = require("../../utils/tracker");
var auth = require("../../utils/auth");

Page({
  data: {
    profile: {},
    userName: "—",
    basicInfo: [],
    behaviorInfo: [],
    hasProfile: false,
    hasBaseline: false,
    hasConsent: false,
    stats: {},
    loggingOut: false,
  },
  onShow: function () {
    if (typeof this.getTabBar === "function" && this.getTabBar()) {
      this.getTabBar().setData({ selected: 4 });
    }
    var that = this;
    var hydrate = require("../../utils/hydrate");
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: "/pages/login/index" });
      return;
    }
    hydrate
      .hydrateFromServer()
      .catch(function (err) {
        console.warn("我的页 hydrate 失败", (err && err.message) || err);
      })
      .then(function () {
        tracker.trackEvent("my", "view");
        that.refresh();
      });
  },
  refresh: function () {
    var profile = ema.getProfile() || {};
    var stats = tracker.getBehaviorStats() || {};
    var hours = stats.checkinHours || [];
    var checkinHoursText = hours.length ? hours.join(", ") : "—";
    var userName =
      profile.userName ||
      profile.user_name ||
      auth.getUserName() ||
      "—";
    this.setData({
      profile: profile,
      userName: userName,
      basicInfo: profileUtil.buildBasicSummary(profile),
      behaviorInfo: [
        { id: "openCount", label: "打开次数", value: stats.openCount || 0, unit: "次" },
        {
          id: "missedDays",
          label: "连续缺测天数",
          value: stats.missedDays || 0,
          unit: "天",
        },
        {
          id: "avgDiary",
          label: "平均日记字数",
          value: stats.avgDiaryWords || 0,
          unit: "字",
        },
        {
          id: "avgVoice",
          label: "平均语音时长",
          value: stats.avgVoiceSec || 0,
          unit: "秒",
        },
        {
          id: "avgVideo",
          label: "平均视频时长",
          value: stats.avgVideoSec || 0,
          unit: "秒",
        },
        {
          id: "voiceSkips",
          label: "语音跳过次数",
          value: stats.voiceSkips || 0,
          unit: "次",
        },
        {
          id: "videoSkips",
          label: "视频跳过次数",
          value: stats.videoSkips || 0,
          unit: "次",
        },
        {
          id: "checkinHours",
          label: "最近打卡时段(时)",
          value: checkinHoursText,
          unit: "时",
        },
      ],
      hasProfile: ema.isOnboardingComplete(),
      hasBaseline: ema.isResearchBound(),
      hasConsent: ema.hasConsent(),
      stats: stats,
    });
  },
  goBehaviorDetail: function () {
    wx.navigateTo({ url: "/pages/my/behavior-detail/index" });
  },
  goProfileDetail: function () {
    if (!ema.isResearchBound()) {
      if (!ema.hasConsent()) {
        wx.redirectTo({ url: "/pages/onboarding/consent/index" });
        return;
      }
      wx.navigateTo({ url: "/pages/onboarding/baseline/index" });
      return;
    }
    wx.navigateTo({ url: "/pages/my/profile-detail/index" });
  },
  goConsent: function () {
    wx.navigateTo({ url: "/pages/onboarding/consent/index?mode=view" });
  },
  onRevokeConsent: function () {
    if (!ema.hasConsent()) return;
    wx.showModal({
      title: "撤回授权",
      content:
        "确认撤回知情同意与隐私授权？撤回后将停止新的数据采集，再次使用需重新同意。",
      confirmText: "确认撤回",
      confirmColor: "#e64340",
      success: function (res) {
        if (!res.confirm) return;
        var at = Date.now();
        tracker.trackEvent("consent", "revoke");
        consentApi
          .recordRevokeLog({ source: "my", page: "my" }, at)
          .then(function (data) {
            ema.applyConsentFromServer({
              has_consent: false,
              status: "revoke",
              at: data.at || at,
            });
          })
          .catch(function (err) {
            console.warn("记录撤回授权失败", err);
            ema.applyConsentFromServer({
              has_consent: false,
              status: "revoke",
              at: at,
            });
          });
        wx.showToast({ title: "已撤回授权", icon: "none" });
        setTimeout(function () {
          wx.reLaunch({ url: "/pages/onboarding/consent/index" });
        }, 500);
      },
    });
  },
  exitStudy: function () {
    wx.showModal({
      title: "退出研究",
      content: "确认解绑研究编号，清除本地数据并退出？",
      confirmText: "确认解绑",
      confirmColor: "#e64340",
      cancelText: "取消",
      cancelColor: "#333",
      success: function (res) {
        if (res.confirm) {
          var at = Date.now();
          tracker.trackEvent("my", "exit_study");
          consentApi
            .recordExitLog({ source: "my", page: "my" }, at)
            .catch(function (err) {
              console.warn("记录退出研究失败", err);
            })
            .then(function () {
              return auth.recordLogoutLog().catch(function (err) {
                console.warn("记录登出失败", err);
              });
            })
            .then(function () {
              auth.clearSession();
              wx.clearStorageSync();
              wx.reLaunch({ url: "/pages/login/index" });
            })
            .catch(function (err) {
              console.warn("退出研究失败", err);
              wx.reLaunch({ url: "/pages/login/index" });
            });
        }
      },
    });
  },
  logout: function () {
    var that = this;
    if (that.data.loggingOut) return;
    that.setData({ loggingOut: true });
    tracker.trackEvent("my", "logout");
    auth
      .logout()
      .then(function () {
        wx.reLaunch({ url: "/pages/login/index" });
      })
      .catch(function () {
        auth.clearSession();
        wx.reLaunch({ url: "/pages/login/index" });
      })
      .then(function () {
        that.setData({ loggingOut: false });
      });
  },
});
