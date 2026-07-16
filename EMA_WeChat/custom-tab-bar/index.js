Component({
  data: {
    selected: 0,
    color: "#999999",
    selectedColor: "#07c160",
    list: [
      {
        pagePath: "pages/home/index",
        text: "首页",
        icon: "t-icon-home",
        iconActive: "t-icon-home-filled",
      },
      {
        pagePath: "pages/records/index",
        text: "记录",
        icon: "t-icon-file",
        iconActive: "t-icon-file-filled",
      },
      {
        pagePath: "pages/trends/index",
        text: "趋势",
        icon: "t-icon-chart-line",
        iconActive: "t-icon-analytics-filled",
      },
      {
        pagePath: "pages/resources/index",
        text: "资源",
        icon: "t-icon-book",
        iconActive: "t-icon-book-filled",
      },
      {
        pagePath: "pages/my/index",
        text: "我的",
        icon: "t-icon-user",
        iconActive: "t-icon-user-filled",
      },
    ],
  },

  lifetimes: {
    attached: function () {
      this.syncSelected();
    },
  },

  pageLifetimes: {
    show: function () {
      this.syncSelected();
    },
  },

  methods: {
    syncSelected: function () {
      var pages = getCurrentPages();
      var page = pages[pages.length - 1];
      if (!page) return;
      var route = page.route;
      var index = -1;
      for (var i = 0; i < this.data.list.length; i++) {
        if (this.data.list[i].pagePath === route) {
          index = i;
          break;
        }
      }
      if (index >= 0 && index !== this.data.selected) {
        this.setData({ selected: index });
      }
    },

    onSwitchTab: function (e) {
      var index = e.currentTarget.dataset.index;
      var path = "/" + this.data.list[index].pagePath;
      wx.switchTab({ url: path });
      this.setData({ selected: index });
    },
  },
});
