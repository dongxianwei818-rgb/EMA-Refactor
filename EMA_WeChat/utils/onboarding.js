var ema = require("./ema");
var sync = require("./sync");
var consentApi = require("./consent");

function applyLoginOnboarding(profile, consent, pullData) {
  ema.setServerProfile({
    user_id: profile.user_id,
    research_id: profile.research_id || null,
    study_status: profile.study_status,
    has_consent: !!consent.has_consent,
    has_baseline: !!profile.has_baseline,
    consent_status: consent.status || null,
    consent_at: consent.at || null,
  });

  ema.applyConsentFromServer(consent);

  if (profile.research_id) {
    if (pullData && pullData.baseline) {
      var baseline = Object.assign({}, pullData.baseline);
      baseline.researchId = baseline.researchId || profile.research_id;
      ema.saveBaseline(baseline);
    }
  } else {
    ema.clearBaseline();
  }
}

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

function syncOnboardingAfterLogin(loginData) {
  var auth = require("./auth");
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
        if (merged.has_consent || merged.research_id) {
          return sync
            .pullFromServer()
            .then(function (pullData) {
              applyLoginOnboarding(merged, consent, pullData);
              return merged;
            })
            .catch(function () {
              applyLoginOnboarding(merged, consent, null);
              return merged;
            });
        }
        applyLoginOnboarding(merged, consent, null);
        return merged;
      });
    });
}

function loginWithOnboardingRedirect(options) {
  options = options || {};
  var shouldRedirect = options.redirect !== false;
  var auth = require("./auth");
  return auth.loginWeChatUser().then(function (loginData) {
    var app = getApp();
    if (app) app._sessionActive = true;

    if (!shouldRedirect) return loginData;

    var redirectUrl = getOnboardingRedirectUrl(loginData);
    if (redirectUrl) {
      if (options.reLaunch) {
        wx.reLaunch({ url: redirectUrl });
      } else {
        wx.redirectTo({ url: redirectUrl });
      }
      return loginData;
    }

    if (options.reLaunch && options.fallbackUrl) {
      wx.reLaunch({ url: options.fallbackUrl });
    }
    return loginData;
  });
}

module.exports = {
  applyLoginOnboarding: applyLoginOnboarding,
  getOnboardingRedirectUrl: getOnboardingRedirectUrl,
  syncOnboardingAfterLogin: syncOnboardingAfterLogin,
  loginWithOnboardingRedirect: loginWithOnboardingRedirect,
};
