var C = require("./constants");
var sync = require("./sync");
var ema = require("./ema");

function fetchDailyTasks(taskDate, sessionId) {
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
    var td = taskDate || ema.getTodayKey();
    var sid = sessionId || ema.getCurrentSessionId() || 1;
    wx.request({
      url: C.API_BASE_URL.replace(/\/$/, "") + "/daily-tasks",
      method: "GET",
      header: { Authorization: "Bearer " + token },
      data: {
        task_date: td,
        session_id: sid,
      },
      success: function (res) {
        var body = res.data || {};
        if (res.statusCode === 200 && body.code === 0) {
          var data = body.data || body;
          ema.applyDailyTasksResponse(data);
          resolve(data);
          return;
        }
        reject(new Error((body && body.message) || "获取任务进度失败"));
      },
      fail: reject,
    });
  });
}

module.exports = {
  fetchDailyTasks: fetchDailyTasks,
};
