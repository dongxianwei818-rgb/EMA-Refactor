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
        that.setData({
          loading: false,
          hasData: !!(data && data.hasData),
          risk: risk,
          metrics: (data && data.metrics) || [],
          stepsTrend: (data && data.stepsTrend) || [],
          stepsAnalytics: (data && data.stepsAnalytics) || {},
          stats: (data && data.stats) || {},
          dayCount: (data && data.dayCount) || DAY_COUNT,
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
        });
        wx.showToast({ title: err.message || '加载失败', icon: 'none' });
      });
  },
});
