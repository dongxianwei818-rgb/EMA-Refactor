/**
 * 入组/知情同意状态：保存在内存会话仓，登录后由 /users/me、sync/pull 填充。
 */
import { getStore } from './sessionStore'

export function getLocalConsent() {
  return getStore().consent
}

export function acceptConsentLocal(at = Date.now()) {
  getStore().consent = { at }
}

export function clearConsentLocal() {
  getStore().consent = null
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
  return getStore().serverProfile || {}
}

export function setServerProfile(profile) {
  getStore().serverProfile = { ...(profile || {}) }
}
