var C = require("./constants");
var sync = require("./sync");
var dt = require("./datetime");

function submitBaselineLog(form, clientAtMs) {
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
    var payload = Object.assign({}, form || {}, {
      client_at: dt.formatClientAt(clientAtMs),
    });
    wx.request({
      url: C.API_BASE_URL.replace(/\/$/, "") + "/baseline/submit-log",
      method: "POST",
      header: {
        "content-type": "application/json",
        Authorization: "Bearer " + token,
      },
      data: payload,
      success: function (res) {
        var body = res.data || {};
        var data = body.data || body;
        if (res.statusCode === 200 && body.code === 0 && data) {
          if (data.token) {
            sync.saveToken(data.token);
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
  submitBaselineLog: submitBaselineLog,
};
