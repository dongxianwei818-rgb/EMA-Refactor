var C = require('../../../utils/constants');
var baselineApi = require('../../../utils/baseline');
var ema = require('../../../utils/ema');
var tracker = require('../../../utils/tracker');

Page({
  data: { sections: C.BASELINE_SECTIONS, form: {} },
  onLoad: function () {
    if (!ema.hasConsent()) {
      wx.redirectTo({ url: '/pages/onboarding/consent/index' });
      return;
    }
    if (ema.isResearchBound()) {
      wx.showToast({ title: '基线测评已完成', icon: 'none' });
      setTimeout(function () {
        wx.switchTab({ url: '/pages/home/index' });
      }, 500);
      return;
    }
    tracker.trackEvent('baseline', 'view');
    tracker.startTaskTimer('baseline');
  },
  onInput: function (e) {
    var id = e.currentTarget.dataset.id;
    var form = this.data.form;
    form[id] = e.detail.value;
    this.setData({ form: form });
  },
  onRadio: function (e) {
    var id = e.currentTarget.dataset.id;
    var form = this.data.form;
    form[id] = e.detail.value;
    this.setData({ form: form });
  },
  validate: function () {
    var f = this.data.form;
    var req = ['researchId', 'age', 'gender', 'grade', 'major', 'onlyChild', 'housing'];
    for (var i = 0; i < req.length; i++) {
      if (!f[req[i]]) {
        wx.showToast({ title: '请完成基本信息', icon: 'none' });
        return false;
      }
    }
    var items = ['course_pressure', 'exam_pressure', 'gpa_pressure', 'job_pressure', 'sleep_habit', 'exercise_freq', 'social_freq', 'phq9_1', 'phq9_2', 'gad7_1', 'gad7_2'];
    for (var j = 0; j < items.length; j++) {
      if (!f[items[j]]) {
        wx.showToast({ title: '请完成学业、生活与量表题', icon: 'none' });
        return false;
      }
    }
    return true;
  },
  onSubmit: function () {
    if (!this.validate()) return;
    var that = this;
    var at = Date.now();
    ema.saveBaseline(Object.assign({}, that.data.form, { at: at }));
    tracker.endTaskTimer('baseline');
    tracker.trackEvent('baseline', 'submit');
    baselineApi
      .submitBaselineLog(that.data.form, at)
      .then(function (data) {
        var sp = ema.getServerProfile();
        sp.research_id = (data && (data.research_id || data.researchId)) || that.data.form.researchId;
        sp.has_baseline = true;
        ema.setServerProfile(sp);
        wx.showToast({ title: '保存成功', icon: 'success' });
        setTimeout(function () {
          wx.switchTab({ url: '/pages/home/index' });
        }, 800);
      })
      .catch(function (err) {
        console.warn('基线提交失败', err);
        wx.showToast({ title: err.message || '提交失败', icon: 'none' });
      });
  },
});
