var ema = require('../../utils/ema');
var tracker = require('../../utils/tracker');
var trendsApi = require('../../utils/trends_api');

var DAY_COUNT = 7;

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
        // 个体异常预警面板排除已在 05/06 单独展示的特征类，避免重复
        var otherAlerts = allAlerts.filter(function (a) {
          var cat = a.category || '';
          return cat !== EMA_CAT && cat !== BEH_CAT;
        });
        risk.alerts = otherAlerts;
        risk.alertCount = otherAlerts.length;
        risk.alertDangerCount = otherAlerts.filter(function (a) {
          return a.level === 'danger';
        }).length;
        risk.alertWarnCount = otherAlerts.filter(function (a) {
          return a.level === 'warn';
        }).length;

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
