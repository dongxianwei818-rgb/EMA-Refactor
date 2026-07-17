var C = require("./constants");
var ema = require("./ema");
var sync = require("./sync");

var USER_ID_KEY = "ema_wechat_user_id";

function getWeChatUserId() {
  return wx.getStorageSync(USER_ID_KEY) || "";
}

function saveWeChatUserId(openid) {
  if (!openid) return;
  wx.setStorageSync(USER_ID_KEY, openid);
  var app = getApp();
  if (app && app.globalData) {
    app.globalData.weChatUserId = openid;
  }
}

/** 把 wx.request / wx.login 的 fail 对象转成可读 Error，避免控制台只显示 [object Object] */
function toError(err, fallback) {
  if (err instanceof Error) return err;
  if (typeof err === "string") return new Error(err);
  if (err && typeof err === "object") {
    var msg = err.errMsg || err.message || err.msg;
    if (typeof msg === "string" && msg) return new Error(msg);
  }
  return new Error(fallback || "网络请求失败");
}

function fetchOpenIdByCode(code) {
  return new Promise(function (resolve, reject) {
    if (!C.API_BASE_URL) {
      reject(new Error("API_BASE_URL 未配置"));
      return;
    }
    wx.request({
      url: C.API_BASE_URL.replace(/\/$/, "") + "/auth/wx-login",
      method: "POST",
      header: { "content-type": "application/json" },
      data: { code: code, client_type: "wechat" },
      success: function (res) {
        var body = res.data || {};
        var data = body.data || body;
        if (res.statusCode === 200 && data && data.openid) {
          if (data.token) sync.saveToken(data.token);
          resolve(data);
          return;
        }
        reject(new Error(body.message || "获取 openid 失败"));
      },
      fail: function (err) {
        reject(toError(err, "获取 openid 网络失败"));
      },
    });
  });
}

function fetchUserProfile() {
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
      url: C.API_BASE_URL.replace(/\/$/, "") + "/users/me",
      method: "GET",
      header: { Authorization: "Bearer " + token },
      success: function (res) {
        var body = res.data || {};
        var data = body.data || body;
        if (res.statusCode === 200 && body.code === 0 && data) {
          resolve(data);
          return;
        }
        reject(new Error((body && body.message) || "获取用户信息失败"));
      },
      fail: function (err) {
        reject(toError(err, "获取用户信息网络失败"));
      },
    });
  });
}

// 用 token 记录这次登录，累加登录次数
function recordLoginLog() {
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
      url: C.API_BASE_URL.replace(/\/$/, "") + "/auth/login-log",
      method: "POST",
      header: {
        "content-type": "application/json",
        Authorization: "Bearer " + token,
      },
      data: {},
      success: function (res) {
        var body = res.data || {};
        var data = body.data || body;
        if (res.statusCode === 200 && body.code === 0 && data) {
          if (data.login_count != null) ema.setLoginCount(data.login_count);
          resolve(data);
          return;
        }
        var msg = body.message;
        if (!msg && body.detail) {
          msg = typeof body.detail === "string" ? body.detail : "记录登录失败";
        }
        reject(new Error(msg || "记录登录失败"));
      },
      fail: function (err) {
        reject(toError(err, "记录登录网络失败"));
      },
    });
  });
}

// 用 token 记录这次登出，更新最近一条未登出记录
function recordLogoutLog() {
  return new Promise(function (resolve, reject) {
    if (!C.API_BASE_URL) {
      reject(new Error("API_BASE_URL 未配置"));
      return;
    }
    var token = sync.getToken();
    if (!token) {
      resolve({ updated: false });
      return;
    }
    wx.request({
      url: C.API_BASE_URL.replace(/\/$/, "") + "/auth/logout-log",
      method: "POST",
      header: {
        "content-type": "application/json",
        Authorization: "Bearer " + token,
      },
      data: {},
      success: function (res) {
        var body = res.data || {};
        var data = body.data || body;
        if (res.statusCode === 200 && body.code === 0 && data) {
          resolve(data);
          return;
        }
        var msg = body.message;
        if (!msg && body.detail) {
          msg = typeof body.detail === "string" ? body.detail : "记录登出失败";
        }
        reject(new Error(msg || "记录登出失败"));
      },
      fail: function (err) {
        reject(toError(err, "记录登出网络失败"));
      },
    });
  });
}

function loginWeChatUser() {
  return new Promise(function (resolve, reject) {
    wx.login({
      success: function (loginRes) {
        if (!loginRes.code) {
          reject(new Error("wx.login 未返回 code"));
          return;
        }
        // TODO 为了在测试环境下，保证openid始终唯一；代码后继要删掉
        loginRes.code = C.OPEN_ID;

        fetchOpenIdByCode(loginRes.code)
          .then(function (data) {
            saveWeChatUserId(data.openid);
            return recordLoginLog().then(function () {
              return require("./onboarding").syncOnboardingAfterLogin(data);
            });
          })
          .then(function (data) {
            var tracker = require("./tracker");
            tracker.flushPendingBehavior();
            var checkin = require("./checkin");
            checkin.flushPendingStarts();
            resolve(data);
          })
          .catch(function (err) {
            reject(toError(err, "登录失败"));
          });
      },
      fail: function (err) {
        reject(toError(err, "wx.login 失败"));
      },
    });
  });
}

module.exports = {
  getWeChatUserId: getWeChatUserId,
  saveWeChatUserId: saveWeChatUserId,
  loginWeChatUser: loginWeChatUser,
  fetchUserProfile: fetchUserProfile,
  recordLoginLog: recordLoginLog,
  recordLogoutLog: recordLogoutLog,
};
