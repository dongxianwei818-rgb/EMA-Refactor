var C = require("../../../utils/constants");
var ema = require("../../../utils/ema");
var emaVoice = require("../../../utils/ema_voice");
var emaFlow = require("../../../utils/ema_flow");
var tracker = require("../../../utils/tracker");

Page({
  data: {
    prompt: "",
    phase: "idle",
    duration: 0,
    recordText: "开始录音",
    /** none=间隔已到 | choice=待选择 | recording=已选重新录制 */
    intervalMode: "none",
    intervalHint: "",
    voiceIntervalDays: 0,
    submitting: false,
  },

  onLoad: function () {
    this.recorder = wx.getRecorderManager();
    this._stopHandled = false;
    this._pendingStopRes = null;
    tracker.trackEvent("voice", "view");
    tracker.startTaskTimer("voice");
    this.setData({
      prompt: C.RANDOMQUESTION+'\n'+C.VOICE_PROMPTS.join("\n"),
      minSec: C.VOICE_MIN_SEC,
      maxSec: C.VOICE_MAX_SEC,
      voiceIntervalDays:C.VOICE_INTERVAL_DAYS
    });
    this.bindRecorderEvents();
    this.checkRecordingInterval();
  },

  buildIntervalHint: function (status) {
    return (
      "距上次语音录制未满 " +
      status.intervalDays +
      " 天（还需约 " +
      status.daysRemaining +
      " 天）。您可以直接进行下一步，或重新录制。"
    );
  },

  checkRecordingInterval: function () {
    var status = ema.getRecordingIntervalStatus("voice");
    if (status.due) return;
    var hint = this.buildIntervalHint(status);
    this.setData({ intervalMode: "choice", intervalHint: hint });
    this.showIntervalModal(hint);
  },

  showIntervalModal: function (hint) {
    var that = this;
    wx.showModal({
      title: "录音间隔提醒",
      content: hint,
      confirmText: "直接进行下一步",
      cancelText: "重新录制",
      success: function (res) {
        if (res.confirm) that.skipToNext();
        else that.chooseReRecord();
      },
    });
  },

  chooseReRecord: function () {
    this.setData({ intervalMode: "recording" });
    tracker.trackEvent("voice", "rer_record_interval");
  },

  skipToNext: function () {
    if (this.data.submitting || this.data.phase === "submitting") return;
    var that = this;
    var at = Date.now();
    ema.markTaskDone("voice");
    ema.saveSubmission("voice", { skip: true, reason: "interval" }, { at: at });
    tracker.endTaskTimer("voice");
    tracker.trackEvent("voice", "skip_interval");
    emaFlow.runStepSubmit({
      page: that,
      title: "提交中…",
      submit: function () {
        return emaVoice.submitVoiceSkipLog(at, ema.getCurrentSessionId(), ema.getTodayKey());
      },
      successToast: "已进入下一步",
      successIcon: "none",
    });
  },

  bindRecorderEvents: function () {
    var that = this;

    this.recorder.onStart(function () {
      that._stopHandled = false;
      that._pendingStopRes = null;
    });

    this.recorder.onError(function (err) {
      console.error("recorder error", err);
      that.resetToIdle("录音失败，请重试");
    });

    this.recorder.onStop(function (res) {
      console.log("recorder onStop", res);
      that._pendingStopRes = res || {};
      that.finishStopWithRes(that._pendingStopRes);
    });
  },

  getElapsedSec: function () {
    if (!this._start) return 0;
    return Math.max(0, Math.floor((Date.now() - this._start) / 1000));
  },

  resetToIdle: function (toast) {
    this.clearTimers();
    this._stopHandled = false;
    this._pendingStopRes = null;
    this.setData({ phase: "idle", recordText: "开始录音" });
    if (toast) wx.showToast({ title: toast, icon: "none" });
  },

  clearTimers: function () {
    if (this._tickTimer) {
      clearInterval(this._tickTimer);
      this._tickTimer = null;
    }
    if (this._fallbackTimer) {
      clearTimeout(this._fallbackTimer);
      this._fallbackTimer = null;
    }
  },

  finishStopWithRes: function (res) {
    if (this._stopHandled) return;
    this._stopHandled = true;
    this.clearTimers();

    var durationMs = (res && res.duration) || 0;
    var duration =
      durationMs >= 1000 ? Math.round(durationMs / 1000) : durationMs;
    if (!duration) duration = this.getElapsedSec();

    if (duration < C.VOICE_MIN_SEC) {
      this.resetToIdle("至少录制 " + C.VOICE_MIN_SEC + " 秒");
      return;
    }

    var path = (res && res.tempFilePath) || "";
    this.submitAndNext(path, duration);
  },

  startRecord: function () {
    var that = this;
    this.bindRecorderEvents();

    var doStart = function () {
      that.clearTimers();
      that._start = Date.now();
      that._stopHandled = false;
      that._pendingStopRes = null;
      that.setData({ phase: "recording", recordText: "录音中…" });
      tracker.trackEvent("voice", "record_start");
      that.recorder.start({
        duration: C.VOICE_MAX_SEC * 1000,
        sampleRate: 16000,
        numberOfChannels: 1,
        encodeBitRate: 48000,
        format: "aac",
      });
      that._tickTimer = setInterval(function () {
        var sec = that.getElapsedSec();
        that.setData({ recordText: sec + " 秒" });
        if (sec >= C.VOICE_MAX_SEC) that.stopRecord();
      }, 400);
    };

    wx.getSetting({
      success: function (res) {
        if (res.authSetting["scope.record"]) {
          doStart();
          return;
        }
        wx.authorize({
          scope: "scope.record",
          success: doStart,
          fail: function () {
            wx.showModal({
              title: "需要麦克风权限",
              confirmText: "去设置",
              success: function (r) {
                if (r.confirm) wx.openSetting();
              },
            });
          },
        });
      },
    });
  },

  stopRecord: function () {
    if (this.data.phase !== "recording") return;

    this.clearTimers();
    var elapsed = this.getElapsedSec();
    this.setData({ phase: "processing", recordText: "处理中…" });
    this._stopHandled = false;

    var that = this;
    try {
      this.recorder.stop();
    } catch (e) {
      console.error("recorder.stop error", e);
    }

    /* 开发者工具/部分真机 onStop 不触发，用本地计时兜底 */
    this._fallbackTimer = setTimeout(function () {
      if (that._stopHandled) return;
      var res = that._pendingStopRes || {
        tempFilePath: "",
        duration: elapsed * 1000,
      };
      if (!res.duration) res.duration = that.getElapsedSec() * 1000;
      that.finishStopWithRes(res);
    }, 800);
  },

  submitAndNext: function (tempFilePath, duration) {
    var that = this;
    if (that.data.submitting) return;
    that.setData({ phase: "submitting", recordText: "提交中…" });
    var at = Date.now();
    that.setData({ submitting: true, phase: "submitting", recordText: "提交中…" });
    ema.markTaskDone("voice");
    ema.saveSubmission(
      "voice",
      {
        path: tempFilePath || "local-pending",
        duration: duration,
        prompt: that.data.prompt,
      },
      { at: at }
    );
    tracker.endTaskTimer("voice");
    tracker.trackEvent("voice", "submit", { duration: duration });
    emaFlow.runStepSubmit({
      page: that,
      title: "上传语音中…",
      submit: function () {
        return emaVoice.submitVoiceLog(
          tempFilePath,
          duration,
          at,
          ema.getCurrentSessionId(),
          ema.getTodayKey()
        );
      },
      successToast: "已提交",
      onError: function (err) {
        console.warn("语音提交失败", err);
        that.resetToIdle(err.message || "提交失败");
      },
    });
  },

  onSkip: function () {
    if (this.data.submitting || this.data.phase === "submitting") return;
    var that = this;
    var at = Date.now();
    that.setData({ submitting: true });
    ema.markVoiceSkipped({ reason: "user_skip", at: at });
    tracker.trackEvent("voice", "skip_voice", { at: at });
    tracker.endTaskTimer("voice");
    emaFlow.runStepSubmit({
      page: that,
      title: "提交中…",
      submit: function () {
        return emaVoice.submitVoiceSkipLog(at, ema.getCurrentSessionId(), ema.getTodayKey());
      },
      successToast: "已跳过",
      successIcon: "none",
    });
  },

  onUnload: function () {
    this.clearTimers();
    if (this.data.phase === "recording") {
      try {
        this.recorder.stop();
      } catch (e) {
        /* ignore */
      }
    }
  },
});
