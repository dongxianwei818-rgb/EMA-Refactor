var C = require("./constants");
var sync = require("./sync");
var ema = require("./ema");
var dt = require("./datetime");

function parseUploadResponse(res) {
  var body = {};
  try {
    body = JSON.parse(res.data || "{}");
  } catch (e) {
    body = {};
  }
  var data = body.data || body;
  if (res.statusCode === 200 && body.code === 0 && data) {
    if (data.daily_tasks) {
      ema.applyServerDailyTasks(data.daily_tasks);
    }
    return data;
  }
  var msg = body.message;
  if (!msg && body.detail) {
    msg = typeof body.detail === "string" ? body.detail : "提交失败";
  }
  throw new Error(msg || "提交失败");
}

function submitVoiceLog(tempFilePath, durationSec, recordedAtMs, sessionId, taskDate) {
  return new Promise(function (resolve, reject) {
    if (!C.API_BASE_URL) {
      reject(new Error("API_BASE_URL 未配置"));
      return;
    }
    if (!tempFilePath) {
      reject(new Error("录音文件不存在，请重新录制"));
      return;
    }
    var token = sync.getToken();
    if (!token) {
      reject(new Error("请先登录后再提交"));
      return;
    }
    wx.uploadFile({
      url: C.API_BASE_URL.replace(/\/$/, "") + "/ema/voice/submit-log",
      filePath: tempFilePath,
      name: "file",
      formData: {
        skip: "0",
        duration_sec: String(durationSec),
        recorded_at: dt.formatClientAt(recordedAtMs),
        session_id: String(sessionId || 1),
        task_date: taskDate || "",
      },
      header: {
        Authorization: "Bearer " + token,
      },
      success: function (res) {
        try {
          resolve(parseUploadResponse(res));
        } catch (err) {
          reject(err);
        }
      },
      fail: reject,
    });
  });
}

function submitVoiceSkipLog(recordedAtMs, sessionId, taskDate) {
  var emaSubmission = require("./ema_submission");
  return emaSubmission.submitStep(
    "voice",
    { skip: true },
    {
      clientAtMs: recordedAtMs,
      sessionId: sessionId,
      taskDate: taskDate,
    }
  );
}

module.exports = {
  submitVoiceLog: submitVoiceLog,
  submitVoiceSkipLog: submitVoiceSkipLog,
};
