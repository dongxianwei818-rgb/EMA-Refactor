var C = require("./constants");
var sync = require("./sync");
var dt = require("./datetime");

var pendingStarts = [];

function postCheckinSession(path, data) {
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
      url: C.API_BASE_URL.replace(/\/$/, "") + path,
      method: "POST",
      header: {
        "content-type": "application/json",
        Authorization: "Bearer " + token,
        "X-Client-Type": "wechat",
      },
      data: data,
      success: function (res) {
        var body = res.data || {};
        if (res.statusCode === 200 && body.code === 0) {
          resolve(body.data || body);
          return;
        }
        var msg = body.message;
        if (!msg && body.detail) {
          msg = typeof body.detail === "string" ? body.detail : "打卡会话同步失败";
        }
        reject(new Error(msg || "打卡会话同步失败"));
      },
      fail: reject,
    });
  });
}

function startCheckinSession(sessionId, startedAtMs, taskDate) {
  var ema = require("./ema");
  var payload = {
    task_date: taskDate || ema.getTodayKey(),
    session_id: sessionId || 1,
    started_at: dt.formatClientAt(startedAtMs),
    checkin_day: ema.getCheckinDaySnapshot() || null,
  };
  return postCheckinSession("/checkin/session/start", payload).catch(function (err) {
    if (err && err.message === "未登录") {
      pendingStarts.push(payload);
    }
    throw err;
  });
}

function completeCheckinSession(sessionId, completedAtMs, taskDate) {
  var ema = require("./ema");
  return postCheckinSession("/checkin/session/complete", {
    task_date: taskDate || ema.getTodayKey(),
    session_id: sessionId || 1,
    completed_at: dt.formatClientAt(completedAtMs),
    checkin_day: ema.getCheckinDaySnapshot() || null,
  });
}

function flushPendingStarts() {
  if (!pendingStarts.length) return;
  var queue = pendingStarts.slice();
  pendingStarts = [];
  queue.forEach(function (payload) {
    postCheckinSession("/checkin/session/start", payload).catch(function (err) {
      console.warn("补发打卡会话失败", err);
    });
  });
}

function notifySessionStarted(sessionId, startedAtMs) {
  startCheckinSession(sessionId, startedAtMs).catch(function (err) {
    console.warn("记录打卡会话失败", err);
  });
}

function notifySessionCompleted(sessionId, completedAtMs) {
  completeCheckinSession(sessionId, completedAtMs).catch(function (err) {
    console.warn("记录打卡完成失败", err);
  });
}

module.exports = {
  startCheckinSession: startCheckinSession,
  completeCheckinSession: completeCheckinSession,
  flushPendingStarts: flushPendingStarts,
  notifySessionStarted: notifySessionStarted,
  notifySessionCompleted: notifySessionCompleted,
};
