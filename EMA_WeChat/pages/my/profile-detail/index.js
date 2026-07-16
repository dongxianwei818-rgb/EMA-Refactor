var ema = require("../../../utils/ema");
var profileUtil = require("../../../utils/profile");

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
    this.refresh();
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
