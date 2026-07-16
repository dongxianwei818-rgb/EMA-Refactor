var C = require("../../../utils/constants");
var ema = require("../../../utils/ema");
var emaVideo = require("../../../utils/ema_video");
var emaFlow = require("../../../utils/ema_flow");
var tracker = require("../../../utils/tracker");

var VIDEO_MIN_SEC = C.VIDEO_MIN_SEC;
var VIDEO_MAX_SEC = C.VOICE_MAX_SEC || 60;

Page({
  data: {
    question: "",
    hideFace: false,
    cameraPosition: "front",
    phase: "idle",
    recordText: "开始录制",
    cameraError: false,
    minSec: VIDEO_MIN_SEC,
    maxSec: VIDEO_MAX_SEC,
    /** none=间隔已到 | choice=待选择 | recording=已选重新录制 */
    intervalMode: "none",
    intervalHint: "",
    submitting: false,
  },

  onLoad: function () {
    this._stopHandled = false;
    this._pendingStopRes = null;
    tracker.trackEvent("video", "view");
    tracker.startTaskTimer("video");
    // var idx = new Date().getDay() % C.VIDEO_QUESTIONS.length;
    this.setData({
      question:C.RANDOMQUESTION +'\n'+ C.VIDEO_QUESTIONS.join("\n"),
      videoIntervalDays: C.VIDEO_INTERVAL_DAYS,
    });
    this.checkRecordingInterval();
  },

  buildIntervalHint: function (status) {
    return (
      "距上次视频录制未满 " +
      status.intervalDays +
      " 天（还需约 " +
      status.daysRemaining +
      " 天）。您可以直接进行下一步，或重新录制。"
    );
  },

  checkRecordingInterval: function () {
    var status = ema.getRecordingIntervalStatus("video");
    if (status.due) return;
    var hint = this.buildIntervalHint(status);
    this.setData({ intervalMode: "choice", intervalHint: hint });
    this.showIntervalModal(hint);
  },

  showIntervalModal: function (hint) {
    var that = this;
    wx.showModal({
      title: "视频间隔提醒",
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
    tracker.trackEvent("video", "rer_record_interval");
  },

  skipToNext: function () {
    if (this.data.submitting || this.data.phase === "submitting") return;
    var that = this;
    var at = Date.now();
    ema.markTaskDone("video");
    ema.saveSubmission("video", { skip: true, reason: "interval" }, { at: at });
    tracker.endTaskTimer("video");
    tracker.trackEvent("video", "skip_interval");
    emaFlow.runStepSubmit({
      page: that,
      title: "提交中…",
      submit: function () {
        return emaVideo.submitVideoSkipLog(at, ema.getCurrentSessionId(), ema.getTodayKey());
      },
      successToast: "已进入下一步",
      successIcon: "none",
    });
  },

  onReady: function () {
    this.cameraCtx = wx.createCameraContext("emaCamera");
  },

  onCameraReady: function () {
    this.setData({ cameraError: false });
  },

  onCameraError: function (e) {
    console.error("camera error", e.detail);
    this.setData({
      cameraError: true,
      recordText: "模拟器无摄像头，请用系统相机",
    });
  },

  toggleHide: function () {
    var hideFace = !this.data.hideFace;
    this.setData({
      hideFace: hideFace,
      cameraPosition: hideFace ? "back" : "front",
    });
    tracker.trackEvent("video", "hide_face_toggle", { hideFace: hideFace });
  },

  getElapsedSec: function () {
    if (!this._recordStart) return 0;
    return Math.floor((Date.now() - this._recordStart) / 1000);
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

  resetIdle: function (text) {
    this.clearTimers();
    this._stopHandled = false;
    this._pendingStopRes = null;
    this.setData({ phase: "idle", recordText: text || "开始录制" });
    if (text) wx.showToast({ title: text, icon: "none" });
  },

  ensureCameraAuth: function (cb) {
    wx.getSetting({
      success: function (res) {
        if (res.authSetting["scope.camera"]) {
          cb(true);
          return;
        }
        wx.authorize({
          scope: "scope.camera",
          success: function () {
            cb(true);
          },
          fail: function () {
            wx.showModal({
              title: "需要摄像头权限",
              confirmText: "去设置",
              success: function (r) {
                if (r.confirm) wx.openSetting();
              },
            });
            cb(false);
          },
        });
      },
    });
  },

  finishRecord: function (res) {
    if (this._stopHandled) return;
    this._stopHandled = true;
    this.clearTimers();

    var durationMs = (res && res.duration) || 0;
    var duration =
      durationMs >= 1000 ? Math.round(durationMs / 1000) : durationMs;
    if (!duration) duration = this.getElapsedSec();

    if (duration < VIDEO_MIN_SEC) {
      this.resetIdle("至少录制 " + VIDEO_MIN_SEC + " 秒");
      return;
    }

    var path = (res && res.tempVideoPath) || (res && res.tempFilePath) || "";
    this.submitAndNext(path, duration);
  },

  startCameraRecord: function () {
    var that = this;
    if (this.data.phase === "recording" || this.data.cameraError) {
      if (this.data.cameraError) this.openSystemCamera();
      return;
    }

    this.ensureCameraAuth(function (ok) {
      if (!ok) return;
      if (!that.cameraCtx) that.cameraCtx = wx.createCameraContext("emaCamera");

      that._recordStart = Date.now();
      that._stopHandled = false;
      that._pendingStopRes = null;
      that.setData({ phase: "recording", recordText: "录制中…" });
      tracker.trackEvent("video", "record_start");

      that.cameraCtx.startRecord({
        timeout: VIDEO_MAX_SEC,
        selfieMirror: that.data.cameraPosition === "front",
        success: function () {},
        fail: function () {
          that.openSystemCamera();
        },
      });

      that._tickTimer = setInterval(function () {
        var sec = that.getElapsedSec();
        that.setData({ recordText: "录制中 " + sec + " 秒" });
        if (sec >= VIDEO_MAX_SEC) that.stopCameraRecord();
      }, 400);
    });
  },

  stopCameraRecord: function () {
    if (this.data.phase !== "recording") return;
    this.clearTimers();
    this.setData({ phase: "processing", recordText: "处理中…" });
    this._stopHandled = false;

    var that = this;
    var elapsed = this.getElapsedSec();

    this._fallbackTimer = setTimeout(function () {
      if (that._stopHandled) return;
      var res = that._pendingStopRes || {
        tempVideoPath: "",
        duration: elapsed * 1000,
      };
      if (!res.duration) res.duration = that.getElapsedSec() * 1000;
      if (res.tempVideoPath || that.getElapsedSec() >= VIDEO_MIN_SEC) {
        that.finishRecord(res);
      } else {
        that.resetIdle("录制结束异常，请用系统相机");
      }
    }, 800);

    try {
      this.cameraCtx.stopRecord({
        success: function (res) {
          that._pendingStopRes = res;
          that.finishRecord(res);
        },
        fail: function () {
          /* 由 fallback 处理 */
        },
      });
    } catch (e) {
      /* 由 fallback 处理 */
    }
  },

  openSystemCamera: function () {
    var that = this;
    if (this.data.phase === "processing" || this.data.phase === "submitting")
      return;

    this.ensureCameraAuth(function (ok) {
      if (!ok) return;
      that.setData({ phase: "processing", recordText: "打开相机…" });
      wx.chooseMedia({
        count: 1,
        mediaType: ["video"],
        sourceType: ["camera"],
        maxDuration: VIDEO_MAX_SEC,
        camera: that.data.cameraPosition,
        success: function (res) {
          var f = res.tempFiles[0];
          var duration = Math.round(f.duration || 0);
          if (duration > 0 && duration < VIDEO_MIN_SEC) {
            that.resetIdle("至少录制 " + VIDEO_MIN_SEC + " 秒");
            return;
          }
          that.finishRecord({
            tempVideoPath: f.tempFilePath,
            tempFilePath: f.tempFilePath,
            duration: duration * 1000,
          });
        },
        fail: function (err) {
          if (err && err.errMsg && err.errMsg.indexOf("cancel") >= 0) {
            that.resetIdle();
            return;
          }
          that.resetIdle("拍摄失败");
        },
      });
    });
  },

  submitAndNext: function (tempFilePath, duration) {
    var that = this;
    if (that.data.submitting) return;
    that.setData({ phase: "submitting", recordText: "提交中…" });
    var at = Date.now();
    ema.markTaskDone("video");
    ema.markVideoDone();
    ema.saveSubmission("video", {
      path: tempFilePath || "local-pending",
      hideFace: that.data.hideFace,
      question: that.data.question,
      duration: duration,
    });
    tracker.endTaskTimer("video");
    tracker.trackEvent("video", "submit", {
      hideFace: that.data.hideFace,
      duration: duration,
    });
    emaFlow.runStepSubmit({
      page: that,
      title: "上传视频中…",
      submit: function () {
        return emaVideo.submitVideoLog(
          tempFilePath,
          duration,
          at,
          ema.getCurrentSessionId(),
          ema.getTodayKey()
        );
      },
      successToast: "已提交",
      onError: function (err) {
        console.warn("视频提交失败", err);
        that.resetIdle(err.message || "提交失败");
      },
    });
  },

  onSkip: function () {
    if (this.data.submitting || this.data.phase === "submitting") return;
    var that = this;
    var at = Date.now();
    ema.markVideoSkipped({ reason: "user_skip" });
    tracker.trackEvent("video", "skip_video", { at: at });
    tracker.endTaskTimer("video");
    emaFlow.runStepSubmit({
      page: that,
      title: "提交中…",
      submit: function () {
        return emaVideo.submitVideoSkipLog(at, ema.getCurrentSessionId(), ema.getTodayKey());
      },
      successToast: "已跳过",
      successIcon: "none",
    });
  },

  onUnload: function () {
    this.clearTimers();
    if (this.data.phase === "recording" && this.cameraCtx) {
      try {
        this.cameraCtx.stopRecord({
          success: function () {},
          fail: function () {},
        });
      } catch (e) {
        /* ignore */
      }
    }
  },
});
