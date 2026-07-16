var C = require("./constants");
var sync = require("./sync");
var dt = require("./datetime");

function saveRiskSnapshot(taskDate, sessionId, computedAtMs) {
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
      url: C.API_BASE_URL.replace(/\/$/, "") + "/risk/snapshot",
      method: "POST",
      header: {
        "content-type": "application/json",
        Authorization: "Bearer " + token,
      },
      data: {
        task_date: taskDate,
        session_id: sessionId || 1,
        computed_at: dt.formatClientAt(computedAtMs),
      },
      success: function (res) {
        var body = res.data || {};
        if (res.statusCode === 200 && body.code === 0) {
          resolve(body.data || body);
          return;
        }
        reject(new Error((body && body.message) || "风险评估保存失败"));
      },
      fail: reject,
    });
  });
}

module.exports = {
  saveRiskSnapshot: saveRiskSnapshot,
};
