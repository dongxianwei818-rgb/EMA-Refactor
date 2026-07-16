var C = require('../../../utils/constants');
var ema = require('../../../utils/ema');
var emaQuestionnaire = require('../../../utils/ema_questionnaire');
var emaFlow = require('../../../utils/ema_flow');
var tracker = require('../../../utils/tracker');

Page({
  data: { questions: C.EMA_QUESTIONS, answers: {}, startAt: 0, submitting: false },
  onLoad: function () {
    tracker.trackEvent('questionnaire', 'view');
    tracker.startTaskTimer('questionnaire');
    var answers = {};
    C.EMA_QUESTIONS.forEach(function (q) {
      answers[q.id] = q.type === 'scale10' ? 5 : '';
    });
    this.setData({ answers: answers, startAt: Date.now() });
  },
  onScale: function (e) {
    var id = e.currentTarget.dataset.id;
    var answers = this.data.answers;
    answers[id] = e.detail.value;
    this.setData({ answers: answers });
  },
  onTernary: function (e) {
    var id = e.currentTarget.dataset.id;
    var answers = this.data.answers;
    answers[id] = e.detail.value;
    this.setData({ answers: answers });
  },
  onSubmit: function () {
    if (this.data.submitting) return;
    var that = this;
    var a = that.data.answers;
    if (!a.negative) {
      wx.showToast({ title: '请回答消极想法条目', icon: 'none' });
      return;
    }
    var sec = Math.round((Date.now() - that.data.startAt) / 1000);
    var at = Date.now();
    ema.markTaskDone('questionnaire');
    ema.saveSubmission('questionnaire', { answers: a, durationSec: sec });
    tracker.endTaskTimer('questionnaire');
    tracker.trackEvent('questionnaire', 'submit', {
      durationSec: sec,
      sessionId: ema.getCurrentSessionId(),
    });
    emaFlow.runStepSubmit({
      page: that,
      title: '提交问卷中…',
      submit: function () {
        return emaQuestionnaire.submitQuestionnaireLog(
          a,
          at,
          ema.getCurrentSessionId(),
          ema.getTodayKey(),
          sec
        );
      },
      successToast: '已提交',
    });
  },
});
