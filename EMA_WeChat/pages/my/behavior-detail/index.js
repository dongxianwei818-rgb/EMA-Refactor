var behaviorUtil = require("../../../utils/behavior");
var tracker = require("../../../utils/tracker");

Page({
  data: {
    sections: [],
    logs: [],
    hasData: false,
  },
  onLoad: function () {
    this.refresh();
  },
  onShow: function () {
    var that = this;
    var hydrate = require("../../../utils/hydrate");
    var auth = require("../../../utils/auth");
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: "/pages/login/index" });
      return;
    }
    hydrate
      .hydrateFromServer()
      .catch(function () {})
      .then(function () {
        tracker.trackEvent("my", "behavior_detail_view");
        that.refresh();
      });
  },
  refresh: function () {
    var detail = behaviorUtil.buildBehaviorDetailSections();
    this.setData({
      sections: detail.sections,
      logs: detail.logs,
      hasData: detail.sections.length > 0 || detail.logs.length > 0,
    });
  },
});
