var ema = require("../../../utils/ema");
var profileUtil = require("../../../utils/profile");
var hydrate = require("../../../utils/hydrate");
var auth = require("../../../utils/auth");

Page({
  data: {
    profile: {},
    sections: [],
    baselineTimeStr: "",
    hasBaseline: false,
  },
  onLoad: function () {
    this.refresh();
  },
  onShow: function () {
    var that = this;
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: "/pages/login/index" });
      return;
    }
    hydrate
      .hydrateFromServer()
      .catch(function () {})
      .then(function () {
        that.refresh();
      });
  },
  refresh: function () {
    var profile = ema.getProfile();
    this.setData({
      profile: profile,
      sections: profileUtil.buildProfileDetailSections(profile),
      baselineTimeStr: profileUtil.formatBaselineTime(profile.at),
      hasBaseline: ema.hasBaseline(),
    });
  },
});
