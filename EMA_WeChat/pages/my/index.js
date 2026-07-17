var ema = require("../../utils/ema");
var consentApi = require("../../utils/consent");
var profileUtil = require("../../utils/profile");
var tracker = require("../../utils/tracker");
var sync = require("../../utils/sync");
var auth = require("../../utils/auth");
var onboarding = require("../../utils/onboarding");

Page({
  data: {
    profile: {},
    basicInfo: [],
    hasProfile: false,
    hasBaseline: false,
    hasConsent: false,
    stats: {},
  },
  onShow: function () {
    if (typeof this.getTabBar === "function" && this.getTabBar()) {
      this.getTabBar().setData({ selected: 4 });
    }
    tracker.trackEvent("my", "view");
    var profile = ema.getProfile();
    this.setData({
      profile: profile,
      basicInfo: profileUtil.buildBasicSummary(profile),
      hasProfile: ema.isOnboardingComplete(),
      hasBaseline: ema.isResearchBound(),
      hasConsent: ema.hasConsent(),
      stats: tracker.getBehaviorStats(),
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
              sync.clearToken();
              wx.clearStorageSync();
              return onboarding.loginWithOnboardingRedirect({
                reLaunch: true,
                fallbackUrl: "/pages/onboarding/consent/index",
              });
            })
            .catch(function (err) {
              console.warn("退出研究后重新登录失败", err);
              wx.showToast({ title: "请重新打开小程序", icon: "none" });
            });
        }
      },
    });
  },
});
