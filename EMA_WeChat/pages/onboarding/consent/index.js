var C = require("../../../utils/constants");
var ema = require("../../../utils/ema");
var consentApi = require("../../../utils/consent");
var tracker = require("../../../utils/tracker");
var sync = require("../../../utils/sync");

function formatConsentTime(ts) {
  if (!ts) return "";
  var d = new Date(ts);
  var y = d.getFullYear();
  var m = d.getMonth() + 1;
  var day = d.getDate();
  var h = d.getHours();
  var min = d.getMinutes();
  return (
    y + "年" + m + "月" + day + "日 " + h + ":" + (min < 10 ? "0" : "") + min
  );
}

Page({
  data: {
    sections: C.CONSENT_SECTIONS,
    agreed: false,
    isReview: false,
    consentTimeStr: "",
    hasAnswered: false,
  },

  onLoad: function (options) {
    var isReview = options.mode === "view";
    tracker.trackEvent("consent", isReview ? "review" : "view");

    if (isReview) {
      this.initReviewMode();
      return;
    }

    if (!sync.getToken()) {
      wx.reLaunch({ url: "/pages/login/index" });
      return;
    }

    if (ema.hasConsent() && !ema.isResearchBound()) {
      wx.redirectTo({ url: "/pages/onboarding/baseline/index" });
      return;
    }
    if (ema.hasConsent() && ema.isResearchBound()) {
      wx.switchTab({ url: "/pages/home/index" });
    }
  },

  initReviewMode: function () {
    wx.setNavigationBarTitle({ title: "查看知情同意" });
    var that = this;
    consentApi
      .fetchConsentStatus()
      .then(function (data) {
        ema.applyConsentFromServer(data);
        if (data.has_consent && data.at) {
          that.setData({
            isReview: true,
            hasAnswered: true,
            agreed: true,
            consentTimeStr: formatConsentTime(data.at),
          });
          return;
        }
        that.setData({
          isReview: true,
          hasAnswered: false,
          agreed: false,
          consentTimeStr: "",
        });
      })
      .catch(function () {
        var record = ema.getConsent();
        if (record && record.at) {
          that.setData({
            isReview: true,
            hasAnswered: true,
            agreed: true,
            consentTimeStr: formatConsentTime(record.at),
          });
        } else {
          that.setData({
            isReview: true,
            hasAnswered: false,
            agreed: false,
            consentTimeStr: "",
          });
        }
      });
  },

  toggleAgree: function () {
    if (this.data.isReview) return;
    this.setData({ agreed: !this.data.agreed });
  },

  onConfirm: function () {
    if (this.data.isReview) return;
    if (!this.data.agreed) return;
    var at = Date.now();
    ema.acceptConsent(at);
    tracker.trackEvent("consent", "accept");
    consentApi
      .recordAcceptLog({ source: "onboarding", page: "consent" }, at)
      .then(function (data) {
        ema.applyConsentFromServer({
          has_consent: true,
          status: "accept",
          at: data.at || at,
        });
      })
      .catch(function (err) {
        console.warn("记录知情同意失败", err);
      });
    wx.showToast({ title: "请继续完成基线测评", icon: "none" });
    setTimeout(function () {
      wx.redirectTo({ url: "/pages/onboarding/baseline/index" });
    }, 1000);
  },

  onBack: function () {
    wx.navigateBack({
      fail: function () {
        wx.switchTab({ url: "/pages/my/index" });
      },
    });
  },
});
