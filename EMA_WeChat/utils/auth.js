var C = require("./constants");
var ema = require("./ema");
var sync = require("./sync");

var USER_ID_KEY = "ema_wechat_user_id";
var USER_NAME_KEY = "ema_wechat_user_name";

function getWeChatUserId() {
  return wx.getStorageSync(USER_ID_KEY) || "";
}

function getUserName() {
  return wx.getStorageSync(USER_NAME_KEY) || "";
}

function saveWeChatUserId(openid) {
  if (!openid) return;
  wx.setStorageSync(USER_ID_KEY, openid);
  var app = getApp();
  if (app && app.globalData) {
    app.globalData.weChatUserId = openid;
  }
}

function saveUserName(userName) {
  if (!userName) return;
  wx.setStorageSync(USER_NAME_KEY, userName);
}

function clearSession() {
  var sessionStore = require("./sessionStore");
  sync.clearToken();
  wx.removeStorageSync(USER_ID_KEY);
  wx.removeStorageSync(USER_NAME_KEY);
  sessionStore.clearLegacyBusinessStorage();
  sessionStore.resetStore();
  sessionStore.invalidateHydrateCache();
  var app = getApp();
  if (app && app.globalData) {
    app.globalData.weChatUserId = "";
  }
}

function isLoggedIn() {
  return !!sync.getToken();
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

function authHeaders(extra) {
  var headers = Object.assign(
    {
      "content-type": "application/json",
      "X-Client-Type": "wechat",
    },
    extra || {}
  );
  var token = sync.getToken();
  if (token) headers.Authorization = "Bearer " + token;
  return headers;
}

/** 用户名密码登录（与 Web 端一致；client_type=wechat；服务端已写登录流水） */
function loginWithPassword(userName, psw) {
  return new Promise(function (resolve, reject) {
    if (!C.API_BASE_URL) {
      reject(new Error("API_BASE_URL 未配置"));
      return;
    }
    var name = (userName || "").trim();
    if (!name || !psw) {
      reject(new Error("请输入用户名和密码"));
      return;
    }
    wx.request({
      url: C.API_BASE_URL.replace(/\/$/, "") + "/auth/login",
      method: "POST",
      header: authHeaders(),
      data: {
        user_name: name,
        psw: psw,
        client_type: "wechat",
      },
      success: function (res) {
        var body = res.data || {};
        var data = body.data || body;
        if (res.statusCode === 200 && body.code === 0 && data && data.token) {
          var sessionStore = require("./sessionStore");
          sessionStore.clearLegacyBusinessStorage();
          sessionStore.resetStore();
          sessionStore.invalidateHydrateCache();
          sync.saveToken(data.token);
          saveWeChatUserId(data.openid || String(data.user_id || ""));
          saveUserName(data.user_name || name);
          if (data.login_count != null) ema.setLoginCount(data.login_count);
          ema.setServerProfile({
            user_id: data.user_id,
            research_id: data.research_id || null,
            study_status: data.study_status,
            has_consent: !!data.has_consent,
            has_baseline: !!data.has_baseline,
          });
          ema.applyConsentFromServer({
            has_consent: !!data.has_consent,
            status: data.has_consent ? "accept" : null,
            at: null,
          });
          resolve(data);
          return;
        }
        var msg = body.message;
        if (!msg && body.detail) {
          msg = typeof body.detail === "string" ? body.detail : "登录失败";
        }
        reject(new Error(msg || "登录失败"));
      },
      fail: function (err) {
        reject(toError(err, "登录网络失败"));
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
      header: authHeaders(),
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
      header: authHeaders(),
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
      header: authHeaders(),
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

/** 登录页修改密码（无需 token；client_type=wechat） */
function changePassword(userName, oldPsw, newPsw) {
  return new Promise(function (resolve, reject) {
    if (!C.API_BASE_URL) {
      reject(new Error("API_BASE_URL 未配置"));
      return;
    }
    var name = (userName || "").trim();
    var old = oldPsw || "";
    var neu = (newPsw || "").trim();
    if (!name || !old || !neu) {
      reject(new Error("请填写用户名、原密码和新密码"));
      return;
    }
    if (neu.length < 6) {
      reject(new Error("新密码至少 6 位"));
      return;
    }
    if (neu === old) {
      reject(new Error("新密码不能与原密码相同"));
      return;
    }
    wx.request({
      url: C.API_BASE_URL.replace(/\/$/, "") + "/auth/change-password",
      method: "POST",
      header: authHeaders(),
      data: {
        user_name: name,
        old_psw: old,
        new_psw: neu,
        client_type: "wechat",
      },
      success: function (res) {
        var body = res.data || {};
        var data = body.data || body;
        if (res.statusCode === 200 && body.code === 0) {
          resolve(data);
          return;
        }
        var msg = body.message;
        if (!msg && body.detail) {
          msg = typeof body.detail === "string" ? body.detail : "修改密码失败";
        }
        reject(new Error(msg || "修改密码失败"));
      },
      fail: function (err) {
        reject(toError(err, "修改密码网络失败"));
      },
    });
  });
}

/** 写入 user_login_logs.logout_at，再清除本地登录态（与 Web logout 一致） */
function logout() {
  var app = getApp();
  if (app) app._sessionActive = false;
  return recordLogoutLog()
    .catch(function (err) {
      console.warn("记录登出失败", (err && err.message) || err);
    })
    .then(function () {
      clearSession();
      return { ok: true };
    });
}

module.exports = {
  getWeChatUserId: getWeChatUserId,
  getUserName: getUserName,
  saveWeChatUserId: saveWeChatUserId,
  saveUserName: saveUserName,
  clearSession: clearSession,
  isLoggedIn: isLoggedIn,
  loginWithPassword: loginWithPassword,
  changePassword: changePassword,
  logout: logout,
  fetchUserProfile: fetchUserProfile,
  recordLoginLog: recordLoginLog,
  recordLogoutLog: recordLogoutLog,
};
