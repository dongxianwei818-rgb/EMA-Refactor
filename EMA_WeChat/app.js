var ema = require("./utils/ema");
var tracker = require("./utils/tracker");
var auth = require("./utils/auth");
var onboarding = require("./utils/onboarding");

App({
  onLaunch: function () {
    this._sessionActive = false;
    this._wasHidden = false;
    tracker.trackEvent("app", "app_launch");
    onboarding
      .loginWithOnboardingRedirect()
      .then(function (loginData) {
        console.log("WeChat user id:", loginData.openid);
      })
      .catch(function (err) {
        console.warn("登录失败", err);
      });
  },
  onShow: function () {
    if (this._wasHidden) {
      this._wasHidden = false;
      auth
        .recordLoginLog()
        .then(function () {
          var app = getApp();
          if (app) app._sessionActive = true;
        })
        .catch(function (err) {
          console.warn("记录登录失败", err);
        });
    }
  },
  onHide: function () {
    this._wasHidden = true;
    if (this._sessionActive) {
      this._sessionActive = false;
      auth.recordLogoutLog().catch(function (err) {
        console.warn("记录登出失败", err);
      });
    }
  },
  globalData: {
    weChatUserId: auth.getWeChatUserId(),
  },
});
