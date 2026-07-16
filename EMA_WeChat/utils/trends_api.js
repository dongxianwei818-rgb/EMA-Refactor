var C = require("./constants");
var sync = require("./sync");

function fetchTrendsOverview(days) {
  return new Promise(function (resolve, reject) {
    if (!C.API_BASE_URL) {
      reject(new Error("API_BASE_URL 未配置"));
      return;
    }
    var token = sync.getToken();
    if (!token) {
      reject(new Error("未登录"));
      return;
    }
    wx.request({
      url:
        C.API_BASE_URL.replace(/\/$/, "") +
        "/trends/overview?days=" +
        (days || 7),
      method: "GET",
      header: {
        Authorization: "Bearer " + token,
      },
      success: function (res) {
        var body = res.data || {};
        if (res.statusCode === 200 && body.code === 0) {
          resolve(body.data || body);
          return;
        }
        reject(new Error((body && body.message) || "趋势数据加载失败"));
      },
      fail: reject,
    });
  });
}

module.exports = {
  fetchTrendsOverview: fetchTrendsOverview,
};
