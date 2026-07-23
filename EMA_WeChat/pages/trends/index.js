var ema = require('../../utils/ema');
var tracker = require('../../utils/tracker');
var trendsApi = require('../../utils/trends_api');

var DAY_COUNT = 7;

function factorTagKey(factor) {
  var src = String((factor && factor.source) || '').toLowerCase();
  var label = String((factor && factor.label) || '');
  if (src.indexOf('voice') >= 0 || label.indexOf('语音') >= 0) return 'voice';
  if (src.indexOf('video') >= 0 || label.indexOf('视频') >= 0) return 'video';
  if (src.indexOf('behavior') >= 0 || label.indexOf('行为') >= 0) return 'behavior';
  if (src.indexOf('question') >= 0 || label.indexOf('问卷') >= 0) return 'questions';
  if (src.indexOf('text') >= 0 || label.indexOf('日记') >= 0 || label.indexOf('文本') >= 0) {
    return 'text';
  }
  if (src.indexOf('step') >= 0 || label.indexOf('步数') >= 0) return 'step';
  if (src.indexOf('baseline') >= 0 || label.indexOf('基线') >= 0) return 'baseline';
  if (src.indexOf('ema') >= 0) return 'ema';
  return 'default';
}

function enrichRiskFactors(risk) {
  if (!risk || !risk.current) return risk;
  var factors = risk.current.factors || [];
  risk.current.factors = factors.map(function (f) {
    return Object.assign({}, f, { tagKey: factorTagKey(f) });
  });
  return risk;
}

Page({
  data: {
    loading: false,
    hasData: false,
    risk: {},
    metrics: [],
    stepsTrend: [],
    stepsAnalytics: {},
    stats: {},
    dayCount: DAY_COUNT,
    emaFeatureAlerts: [],
    emaFeatureDangerCount: 0,
    emaFeatureWarnCount: 0,
    behaviorAnalysisAlerts: [],
    behaviorDangerCount: 0,
    behaviorWarnCount: 0,
  },

  onShow: function () {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 });
    }
    tracker.trackEvent('trends', 'view');
    this.refresh();
  },

  refresh: function () {
    var that = this;
    that.setData({ loading: true });
    trendsApi
      .fetchTrendsOverview(DAY_COUNT)
      .then(function (data) {
        var risk = (data && data.risk) || {};
        if (!risk.forecast30) {
          risk.forecast30 = {
            trendLabel: '',
            peakLevelLabel: '',
            peakLevelClass: '',
            summary: '',
            highRiskDays: 0,
            mediumRiskDays: 0,
            weeks: [],
            days: [],
          };
        }
        if (!risk.forecastAlerts) risk.forecastAlerts = [];
        if (risk.forecastAlertCount == null) {
          risk.forecastAlertCount = risk.forecastAlerts.length;
        }
        if (!risk.alerts) risk.alerts = [];

        var EMA_CAT = 'EMA五特性抽取风险预警';
        var BEH_CAT = '用户行为分析风险预警';
        var allAlerts = risk.alerts || [];
        var emaFeatureAlerts = allAlerts.filter(function (a) {
          return (a.category || '') === EMA_CAT;
        });
        var behaviorAnalysisAlerts = allAlerts.filter(function (a) {
          return (a.category || '') === BEH_CAT;
        });
        // 个体异常预警展示全部类别（含特征/行为）；下方专项面板仍单独展示
        if (risk.alertCount == null) risk.alertCount = allAlerts.length;
        if (risk.alertDangerCount == null) {
          risk.alertDangerCount = allAlerts.filter(function (a) {
            return a.level === 'danger';
          }).length;
        }
        if (risk.alertWarnCount == null) {
          risk.alertWarnCount = allAlerts.filter(function (a) {
            return a.level === 'warn';
          }).length;
        }
        risk = enrichRiskFactors(risk);

        that.setData({
          loading: false,
          hasData: !!(data && data.hasData),
          risk: risk,
          metrics: (data && data.metrics) || [],
          stepsTrend: (data && data.stepsTrend) || [],
          stepsAnalytics: (data && data.stepsAnalytics) || {},
          stats: (data && data.stats) || {},
          dayCount: (data && data.dayCount) || DAY_COUNT,
          emaFeatureAlerts: emaFeatureAlerts,
          emaFeatureDangerCount: emaFeatureAlerts.filter(function (a) {
            return a.level === 'danger';
          }).length,
          emaFeatureWarnCount: emaFeatureAlerts.filter(function (a) {
            return a.level === 'warn';
          }).length,
          behaviorAnalysisAlerts: behaviorAnalysisAlerts,
          behaviorDangerCount: behaviorAnalysisAlerts.filter(function (a) {
            return a.level === 'danger';
          }).length,
          behaviorWarnCount: behaviorAnalysisAlerts.filter(function (a) {
            return a.level === 'warn';
          }).length,
        });
      })
      .catch(function (err) {
        console.warn('趋势数据加载失败', err);
        that.setData({
          loading: false,
          hasData: false,
          risk: {},
          metrics: [],
          stepsTrend: [],
          stepsAnalytics: {},
          stats: {},
          emaFeatureAlerts: [],
          emaFeatureDangerCount: 0,
          emaFeatureWarnCount: 0,
          behaviorAnalysisAlerts: [],
          behaviorDangerCount: 0,
          behaviorWarnCount: 0,
        });
        wx.showToast({ title: err.message || '加载失败', icon: 'none' });
      });
  },
});
