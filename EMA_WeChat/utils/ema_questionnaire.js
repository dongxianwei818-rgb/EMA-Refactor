var emaSubmission = require("./ema_submission");

function submitQuestionnaireLog(answers, answeredAtMs, sessionId, taskDate, durationSec) {
  var payload = { answers: answers || {} };
  if (durationSec != null) payload.durationSec = durationSec;
  return emaSubmission.submitStep("questionnaire", payload, {
    clientAtMs: answeredAtMs,
    sessionId: sessionId,
    taskDate: taskDate,
  });
}

module.exports = {
  submitQuestionnaireLog: submitQuestionnaireLog,
};
