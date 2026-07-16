var ema = require("./ema");
var auth = require("./auth");

var TOKEN_KEY = "ema_auth_token";

function getToken() {
  return wx.getStorageSync(TOKEN_KEY) || "";
}

function saveToken(token) {
  if (token) wx.setStorageSync(TOKEN_KEY, token);
}

function clearToken() {
  wx.removeStorageSync(TOKEN_KEY);
}

function collectPayload() {
  return {
    consent: ema.getConsent(),
    baseline: wx.getStorageSync("ema_baseline") || null,
    login_count: ema.getLoginCount(),
    steps_history: wx.getStorageSync("ema_steps_history") || [],
    steps_baseline: wx.getStorageSync("ema_steps_baseline") || null,
    video_skips: ema.getVideoSkips(),
    voice_skips: ema.getVoiceSkips(),
    checkin_day: wx.getStorageSync("ema_checkin_day") || null,
    video_dates: wx.getStorageSync("ema_video_dates") || [],
  };
}

function pushToServer() {
  return new Promise(function (resolve, reject) {
    var C = require("./constants");
    if (!C.API_BASE_URL) {
      reject(new Error("API_BASE_URL 未配置"));
      return;
    }
    var token = getToken();
    if (!token) {
      reject(new Error("未登录，无法同步"));
      return;
    }
    wx.request({
      url: C.API_BASE_URL.replace(/\/$/, "") + "/sync/push",
      method: "POST",
      header: {
        "content-type": "application/json",
        Authorization: "Bearer " + token,
      },
      data: collectPayload(),
      success: function (res) {
        if (res.statusCode === 200 && res.data && res.data.code === 0) {
          var data = res.data.data || {};
          if (data.token) {
            saveToken(data.token);
          }
          resolve(data);
          return;
        }
        reject(new Error((res.data && res.data.message) || "同步失败"));
      },
      fail: reject,
    });
  });
}

function pullFromServer() {
  return new Promise(function (resolve, reject) {
    var C = require("./constants");
    if (!C.API_BASE_URL) {
      reject(new Error("API_BASE_URL 未配置"));
      return;
    }
    var token = getToken();
    if (!token) {
      reject(new Error("未登录"));
      return;
    }
    wx.request({
      url: C.API_BASE_URL.replace(/\/$/, "") + "/sync/pull",
      method: "GET",
      header: { Authorization: "Bearer " + token },
      success: function (res) {
        if (res.statusCode === 200 && res.data && res.data.code === 0) {
          resolve(res.data.data);
          return;
        }
        reject(new Error((res.data && res.data.message) || "拉取失败"));
      },
      fail: reject,
    });
  });
}

module.exports = {
  getToken: getToken,
  saveToken: saveToken,
  clearToken: clearToken,
  collectPayload: collectPayload,
  pushToServer: pushToServer,
  pullFromServer: pullFromServer,
};
