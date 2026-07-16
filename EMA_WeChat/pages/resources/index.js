var C = require("../../utils/constants");
var tracker = require("../../utils/tracker");

Page({
  data: {
    sections: [],
  },

  onLoad: function () {
    this.loadSections();
  },

  onShow: function () {
    if (typeof this.getTabBar === "function" && this.getTabBar()) {
      this.getTabBar().setData({ selected: 3 });
    }
    tracker.trackEvent("resources", "view");
    if (!this.data.sections.length) {
      this.loadSections();
    }
  },

  loadSections: function () {
    var sections = C.RESOURCE_SECTIONS || [];
    this.setData({ sections: sections });
  },

  onCall: function (e) {
    var phone = e.currentTarget.dataset.phone;
    if (!phone) return;
    wx.makePhoneCall({
      phoneNumber: phone,
      fail: function () {
        wx.setClipboardData({
          data: phone,
          success: function () {
            wx.showToast({ title: "号码已复制", icon: "none" });
          },
        });
      },
    });
  },

  onCopy: function (e) {
    var text = e.currentTarget.dataset.text;
    if (!text) return;
    wx.setClipboardData({
      data: text,
      success: function () {
        wx.showToast({ title: "已复制", icon: "success" });
      },
    });
  },
});
