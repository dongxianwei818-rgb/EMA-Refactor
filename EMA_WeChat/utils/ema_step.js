var emaSubmission = require("./ema_submission");

function submitStepLog(steps, source, recordedAtMs, sessionId, taskDate, analytics) {
  var payload = {
    steps: steps,
    source: source || "manual",
  };
  if (analytics) payload.analytics = analytics;
  return emaSubmission.submitStep("steps", payload, {
    clientAtMs: recordedAtMs,
    sessionId: sessionId,
    taskDate: taskDate,
  });
}

module.exports = {
  submitStepLog: submitStepLog,
};
