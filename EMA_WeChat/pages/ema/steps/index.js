var ema = require("../../../utils/ema");
var emaStep = require("../../../utils/ema_step");
var emaFlow = require("../../../utils/ema_flow");
var tracker = require("../../../utils/tracker");
var werun = require("../../../utils/werun");
var sync = require("../../../utils/sync");
var riskApi = require("../../../utils/risk_api");

Page({
  data: {
    stepCount: "--",
    loading: false,
    submitting: false,
    useManual: false,
    analytics: {},
    stepSource: "",
  },
  onLoad: function () {
    tracker.trackEvent("steps", "view");
    tracker.startTaskTimer("steps");
    this.setData({ analytics: ema.getStepsAnalytics() });
  },
  fetchSteps: function () {
    var that = this;
    that.setData({ loading: true });
    wx.getSetting({
      success: function (settingRes) {
        if (settingRes.authSetting["scope.werun"]) {
          that.requestWeRunData();
          return;
        }
        wx.authorize({
          scope: "scope.werun",
          success: function () {
            that.requestWeRunData();
          },
          fail: function () {
            wx.showModal({
              title: "需要授权",
              content: "请在设置中允许「微信运动」权限，或改用手动输入步数。",
              confirmText: "去设置",
              success: function (res) {
                if (res.confirm) wx.openSetting();
              },
            });
            that.setData({ useManual: true, loading: false });
          },
        });
      },
      fail: function () {
        that.setData({ useManual: true, loading: false });
      },
    });
  },
  requestWeRunData: function () {
    var that = this;
    wx.login({
      success: function (loginRes) {
        if (!loginRes.code) {
          that.setData({ useManual: true, loading: false });
          wx.showToast({ title: "登录失败", icon: "none" });
          return;
        }
        wx.getWeRunData({
          success: function (werunRes) {
            werun
              .fetchTodaySteps(
                loginRes.code,
                werunRes.encryptedData,
                werunRes.iv,
              )
              .then(function (data) {
                that.setData({
                  stepCount: data.steps,
                  useManual: false,
                  loading: false,
                  stepSource: data.source || "werun",
                  analytics: ema.getStepsAnalytics(),
                });
                wx.showToast({
                  title: "已获取" + data.steps + "步",
                  icon: "success",
                });
              })
              .catch(function (err) {
                console.warn("werun decrypt fail", err);
                wx.showToast({
                  title: err.message || "获取失败",
                  icon: "none",
                });
                that.setData({ useManual: true, loading: false });
              });
          },
          fail: function () {
            wx.showToast({ title: "无法读取微信运动", icon: "none" });
            that.setData({ useManual: true, loading: false });
          },
        });
      },
      fail: function () {
        that.setData({ useManual: true, loading: false });
      },
    });
  },
  onManual: function (e) {
    this.setData({ stepCount: e.detail.value || "--", stepSource: "manual" });
  },
  onSubmit: function () {
    if (this.data.submitting) return;
    var steps = this.data.stepCount;
    if (!steps || steps === "--") {
      wx.showToast({ title: "请填写步数", icon: "none" });
      return;
    }
    var that = this;
    var n = Number(steps);
    var at = Date.now();
    var source = this.data.stepSource || "manual";
    that.setData({ submitting: true });
    ema.saveStepsHistory(n);
    ema.markTaskDone("steps");
    ema.saveSubmission(
      "steps",
      {
        steps: n,
        source: source,
        analytics: ema.getStepsAnalytics(),
      },
      { at: at }
    );
    tracker.endTaskTimer("steps");
    tracker.trackEvent("steps", "submit", { steps: n });
    emaFlow.runStepSubmit({
      page: that,
      title: "完成打卡中…",
      goNext: false,
      submit: function () {
        return emaStep
          .submitStepLog(
            n,
            source,
            at,
            ema.getCurrentSessionId(),
            ema.getTodayKey(),
            ema.getStepsAnalytics(),
          )
          .then(function () {
            return riskApi.saveRiskSnapshot(
              ema.getTodayKey(),
              ema.getCurrentSessionId(),
              at,
            );
          })
          .then(function () {
            return sync.pushToServer();
          });
      },
      successToast: "今日打卡完成",
      onSuccess: function () {
        emaFlow.goHome(400);
      },
      onError: function (err) {
        console.warn("步数或风险评估提交失败", err);
        wx.showToast({ title: err.message || "提交失败", icon: "none" });
      },
    });
  },
});
