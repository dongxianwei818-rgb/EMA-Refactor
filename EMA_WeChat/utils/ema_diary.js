var emaSubmission = require("./ema_submission");

function submitDiaryLog(text, length, writtenAtMs, sessionId, taskDate) {
  return emaSubmission.submitStep(
    "diary",
    { text: text, length: length },
    {
      clientAtMs: writtenAtMs,
      sessionId: sessionId,
      taskDate: taskDate,
    }
  );
}

module.exports = {
  submitDiaryLog: submitDiaryLog,
};
