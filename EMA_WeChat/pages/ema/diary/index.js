var C = require("../../../utils/constants");
var ema = require("../../../utils/ema");
var emaDiary = require("../../../utils/ema_diary");
var emaFlow = require("../../../utils/ema_flow");
var tracker = require("../../../utils/tracker");

Page({
  data: {
    prompt: "",
    text: "",
    len: 0,
    valid: false,
    minLen: C.DIARY_MIN,
    maxLen: C.DIARY_MAX,
    submitting: false,
  },
  onLoad: function () {
    tracker.trackEvent("diary", "view");
    tracker.startTaskTimer("diary");
    this.setData({ prompt: C.DIARY_PROMPTS.join("\n") });
  },
  onInput: function (e) {
    var text = e.detail.value || "";
    var len = text.length;
    this.setData({
      text: text,
      len: len,
      valid: len >= C.DIARY_MIN && len <= C.DIARY_MAX,
    });
  },
  onSubmit: function () {
    if (!this.data.valid || this.data.submitting) return;
    var that = this;
    var at = Date.now();
    ema.markTaskDone("diary");
    ema.saveSubmission("diary", {
      text: that.data.text,
      prompt: that.data.prompt,
    });
    tracker.endTaskTimer("diary");
    tracker.trackEvent("diary", "submit", { length: that.data.len });
    emaFlow.runStepSubmit({
      page: that,
      title: "提交日记中…",
      submit: function () {
        return emaDiary.submitDiaryLog(
          that.data.text,
          that.data.len,
          at,
          ema.getCurrentSessionId(),
          ema.getTodayKey()
        );
      },
      successToast: "已提交",
    });
  },
});
