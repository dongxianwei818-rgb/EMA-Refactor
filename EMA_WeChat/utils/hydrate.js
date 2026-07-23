/**
 * 从服务端拉取用户业务数据并写入内存会话仓。
 * Storage 仅保留登录凭证；业务数据一律以接口为准（与 Web hydrate 一致）。
 */
var sync = require("./sync");
var dailyTasksApi = require("./daily_tasks_api");
var ema = require("./ema");
var sessionStore = require("./sessionStore");

var hydratePromise = null;
var HYDRATE_TTL_MS = 30 * 1000;

/**
 * @param {{ force?: boolean }} [options]
 */
function hydrateFromServer(options) {
  options = options || {};
  var force = !!options.force;
  var now = Date.now();
  if (!force && hydratePromise) return hydratePromise;
  if (!force && now - sessionStore.getLastHydratedAt() < HYDRATE_TTL_MS) {
    return Promise.resolve(true);
  }
  if (!sync.getToken()) {
    return Promise.reject(new Error("未登录"));
  }

  hydratePromise = Promise.resolve()
    .then(function () {
      sessionStore.clearLegacyBusinessStorage();
      return sync.pullFromServer();
    })
    .then(function (data) {
      ema.applySyncPullPayload(data);

      var sp = ema.getServerProfile() || {};
      if (data && data.research_id) {
        sp.research_id = data.research_id;
        sp.has_baseline = true;
      }
      if (data && data.consent && data.consent.at) {
        sp.has_consent = true;
        sp.consent_at = data.consent.at;
        ema.applyConsentFromServer({
          has_consent: true,
          status: "accept",
          at: data.consent.at,
        });
      }
      if (data && data.study_status) sp.study_status = data.study_status;
      if (data && data.login_count != null) {
        ema.setLoginCount(data.login_count);
      }
      ema.setServerProfile(sp);

      var sessionId = ema.getCurrentSessionId();
      return dailyTasksApi
        .fetchDailyTasks(ema.getTodayKey(), sessionId)
        .catch(function (err) {
          console.warn("拉取今日任务失败", (err && err.message) || err);
        })
        .then(function () {
          sessionStore.markHydrated();
          return data;
        });
    });

  return hydratePromise
    .then(function (data) {
      return data;
    })
    .finally(function () {
      hydratePromise = null;
    });
}

module.exports = {
  hydrateFromServer: hydrateFromServer,
  invalidateHydrateCache: sessionStore.invalidateHydrateCache,
};
