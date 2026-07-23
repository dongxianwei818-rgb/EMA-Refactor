var ema = require("./ema");
var consentApi = require("./consent");
var hydrate = require("./hydrate");

function getOnboardingRedirectUrl(profile) {
  if (!profile) return null;
  if (!profile.has_consent) {
    return "/pages/onboarding/consent/index";
  }
  if (!profile.research_id) {
    return "/pages/onboarding/baseline/index";
  }
  return null;
}

/**
 * 登录后：拉 /users/me + consent，再 hydrate（sync/pull + daily-tasks），与 Web 一致。
 */
function syncOnboardingAfterLogin(loginData) {
  var auth = require("./auth");
  loginData = loginData || {};
  return auth
    .fetchUserProfile()
    .then(function (profile) {
      return consentApi.fetchConsentStatus().then(function (consent) {
        var merged = {
          openid: profile.openid || loginData.openid,
          user_id: profile.user_id || loginData.user_id,
          research_id: profile.research_id || null,
          study_status: profile.study_status,
          has_baseline: !!profile.has_baseline,
          has_consent: !!consent.has_consent,
        };

        ema.setServerProfile({
          user_id: merged.user_id,
          research_id: merged.research_id,
          study_status: merged.study_status,
          has_consent: merged.has_consent,
          has_baseline: merged.has_baseline,
          consent_status: consent.status || null,
          consent_at: consent.at || null,
        });
        ema.applyConsentFromServer(consent);

        if (!merged.has_consent && !merged.research_id) {
          ema.clearBaseline();
          return merged;
        }

        return hydrate
          .hydrateFromServer({ force: true })
          .then(function () {
            var sp = ema.getServerProfile() || {};
            if (merged.research_id) {
              sp.research_id = merged.research_id;
              sp.has_baseline = true;
              ema.setServerProfile(sp);
            }
            if (!merged.research_id && !ema.isResearchBound()) {
              ema.clearBaseline();
            }
            return Object.assign({}, merged, {
              has_consent: ema.hasConsent(),
              has_baseline: !!ema.getServerProfile().has_baseline,
              research_id:
                ema.getServerProfile().research_id || merged.research_id,
            });
          })
          .catch(function (err) {
            console.warn("hydrate 失败", (err && err.message) || err);
            return merged;
          });
      });
    });
}

function redirectAfterLogin(loginData, options) {
  options = options || {};
  var app = getApp();
  if (app) app._sessionActive = true;

  if (options.redirect === false) return loginData;

  var redirectUrl = getOnboardingRedirectUrl(loginData);
  if (redirectUrl) {
    if (options.reLaunch) {
      wx.reLaunch({ url: redirectUrl });
    } else {
      wx.redirectTo({ url: redirectUrl });
    }
    return loginData;
  }

  if (options.reLaunch) {
    wx.reLaunch({ url: options.fallbackUrl || "/pages/home/index" });
  }
  return loginData;
}

/** 密码登录后完成 onboarding 同步与跳转 */
function loginWithPasswordAndRedirect(userName, psw, options) {
  options = options || {};
  var auth = require("./auth");
  return auth.loginWithPassword(userName, psw).then(function (data) {
    return syncOnboardingAfterLogin(data).then(function (loginData) {
      var tracker = require("./tracker");
      tracker.flushPendingBehavior();
      var checkin = require("./checkin");
      checkin.flushPendingStarts();
      return redirectAfterLogin(loginData, options);
    });
  });
}

/** 已有 token 时恢复会话；无 token 则跳转登录页 */
function resumeSessionWithOnboarding(options) {
  options = options || {};
  var auth = require("./auth");
  if (!auth.isLoggedIn()) {
    wx.reLaunch({ url: "/pages/login/index" });
    return Promise.reject(new Error("未登录"));
  }
  return syncOnboardingAfterLogin({})
    .then(function (loginData) {
      return redirectAfterLogin(loginData, options);
    })
    .catch(function (err) {
      console.warn("恢复会话失败", (err && err.message) || err);
      auth.clearSession();
      wx.reLaunch({ url: "/pages/login/index" });
      throw err;
    });
}

/** @deprecated 改用 loginWithPasswordAndRedirect / resumeSessionWithOnboarding */
function loginWithOnboardingRedirect(options) {
  return resumeSessionWithOnboarding(options);
}

module.exports = {
  getOnboardingRedirectUrl: getOnboardingRedirectUrl,
  syncOnboardingAfterLogin: syncOnboardingAfterLogin,
  loginWithPasswordAndRedirect: loginWithPasswordAndRedirect,
  resumeSessionWithOnboarding: resumeSessionWithOnboarding,
  loginWithOnboardingRedirect: loginWithOnboardingRedirect,
};
