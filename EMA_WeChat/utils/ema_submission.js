var C = require("./constants");
var sync = require("./sync");
var ema = require("./ema");
var dt = require("./datetime");

function submitStep(type, payload, meta) {
  return new Promise(function (resolve, reject) {
    if (!C.API_BASE_URL) {
      reject(new Error("API_BASE_URL 未配置"));
      return;
    }
    var token = sync.getToken();
    if (!token) {
      reject(new Error("请先登录后再提交"));
      return;
    }
    meta = meta || {};
    wx.request({
      url: C.API_BASE_URL.replace(/\/$/, "") + "/ema/submission/submit",
      method: "POST",
      header: {
        "content-type": "application/json",
        Authorization: "Bearer " + token,
      },
      data: {
        type: type,
        payload: payload || {},
        session_id: meta.sessionId || 1,
        task_date: meta.taskDate,
        client_at: dt.formatClientAt(meta.clientAtMs),
      },
      success: function (res) {
        var body = res.data || {};
        var data = body.data || body;
        if (res.statusCode === 200 && body.code === 0 && data) {
          if (data.daily_tasks) {
            ema.applyServerDailyTasks(data.daily_tasks);
          }
          resolve(data);
          return;
        }
        var msg = body.message;
        if (!msg && body.detail) {
          msg = typeof body.detail === "string" ? body.detail : "提交失败";
        }
        reject(new Error(msg || "提交失败"));
      },
      fail: reject,
    });
  });
}

module.exports = {
  submitStep: submitStep,
};
