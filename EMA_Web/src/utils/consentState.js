/**
 * 本地知情同意状态（对齐 EMA_WeChat/utils/ema.js 的 ema_consent / server profile）
 */
const CONSENT_KEY = 'ema_consent'
const SERVER_PROFILE_KEY = 'ema_server_profile'

export function getLocalConsent() {
  try {
    return JSON.parse(localStorage.getItem(CONSENT_KEY) || 'null')
  } catch {
    return null
  }
}

export function acceptConsentLocal(at = Date.now()) {
  localStorage.setItem(CONSENT_KEY, JSON.stringify({ at }))
}

export function clearConsentLocal() {
  localStorage.removeItem(CONSENT_KEY)
}

export function applyConsentFromServer(consentData) {
  const sp = getServerProfile()
  sp.has_consent = !!(consentData && consentData.has_consent)
  sp.consent_status = (consentData && consentData.status) || null
  sp.consent_at = (consentData && consentData.at) || null
  setServerProfile(sp)
  if (sp.has_consent && sp.consent_at) {
    acceptConsentLocal(sp.consent_at)
  } else if (!sp.has_consent) {
    clearConsentLocal()
  }
}

export function hasConsent() {
  const sp = getServerProfile()
  if (typeof sp.has_consent === 'boolean') return sp.has_consent
  const local = getLocalConsent()
  return !!(local && local.at)
}

export function getServerProfile() {
  try {
    return JSON.parse(localStorage.getItem(SERVER_PROFILE_KEY) || '{}')
  } catch {
    return {}
  }
}

export function setServerProfile(profile) {
  localStorage.setItem(SERVER_PROFILE_KEY, JSON.stringify(profile || {}))
}
