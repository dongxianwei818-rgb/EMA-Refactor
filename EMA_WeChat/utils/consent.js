var C = require("./constants");
var sync = require("./sync");
var dt = require("./datetime");

function postConsentLog(path, eventInfo, clientAtMs) {
  return new Promise(function (resolve, reject) {
    if (!C.API_BASE_URL) {
      reject(new Error("API_BASE_URL 未配置"));
      return;
    }
    var token = sync.getToken();
    if (!token) {
      reject(new Error("请先登录后再记录"));
      return;
    }
    wx.request({
      url: C.API_BASE_URL.replace(/\/$/, "") + path,
      method: "POST",
      header: {
        "content-type": "application/json",
        Authorization: "Bearer " + token,
      },
      data: {
        event_info: eventInfo || {},
        client_at: dt.formatClientAt(clientAtMs),
      },
      success: function (res) {
        var body = res.data || {};
        var data = body.data || body;
        if (res.statusCode === 200 && body.code === 0 && data) {
          resolve(data);
          return;
        }
        var msg = body.message;
        if (!msg && body.detail) {
          msg = typeof body.detail === "string" ? body.detail : "记录失败";
        }
        reject(new Error(msg || "记录失败"));
      },
      fail: reject,
    });
  });
}

function fetchConsentStatus() {
  return new Promise(function (resolve, reject) {
    if (!C.API_BASE_URL) {
      reject(new Error("API_BASE_URL 未配置"));
      return;
    }
    var token = sync.getToken();
    if (!token) {
      reject(new Error("请先登录"));
      return;
    }
    wx.request({
      url: C.API_BASE_URL.replace(/\/$/, "") + "/consent/status",
      method: "GET",
      header: { Authorization: "Bearer " + token },
      success: function (res) {
        var body = res.data || {};
        var data = body.data || body;
        if (res.statusCode === 200 && body.code === 0 && data) {
          resolve(data);
          return;
        }
        reject(new Error((body && body.message) || "获取授权状态失败"));
      },
      fail: reject,
    });
  });
}

function recordAcceptLog(eventInfo, clientAtMs) {
  return postConsentLog("/consent/accept-log", eventInfo, clientAtMs);
}

function recordRevokeLog(eventInfo, clientAtMs) {
  return postConsentLog("/consent/revoke-log", eventInfo, clientAtMs);
}

function recordExitLog(eventInfo, clientAtMs) {
  return postConsentLog("/consent/exit-log", eventInfo, clientAtMs);
}

module.exports = {
  fetchConsentStatus: fetchConsentStatus,
  recordAcceptLog: recordAcceptLog,
  recordRevokeLog: recordRevokeLog,
  recordExitLog: recordExitLog,
};
