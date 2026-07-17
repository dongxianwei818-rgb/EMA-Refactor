/**
 * 入组状态门控：避免每次路由跳转都打 /users/me + /consent/status
 * 优先读本地 profile；冷启动或强制刷新时才同步一次服务端。
 */
import { fetchProfile } from '../api/auth'
import { applyConsentFromServer, getServerProfile, setServerProfile } from './consentState'

const TTL_MS = 5 * 60 * 1000

let syncedAt = 0
let inflight = null

export function invalidateOnboardingGate() {
  syncedAt = 0
  inflight = null
}

export function markOnboardingSynced() {
  syncedAt = Date.now()
}

function applyProfile(profile) {
  if (!profile) return
  const prev = getServerProfile()
  setServerProfile({
    ...prev,
    research_id: profile.research_id ?? prev.research_id,
    has_baseline: profile.has_baseline ?? prev.has_baseline,
    has_consent: profile.has_consent ?? prev.has_consent,
  })
  if (typeof profile.has_consent === 'boolean') {
    applyConsentFromServer({
      has_consent: profile.has_consent,
      status: profile.consent_status || (profile.has_consent ? 'accept' : null),
      at: profile.consent_at || prev.consent_at || null,
    })
  }
}

/** 本地已有明确同意/基线态时，跳过网络 */
export function hasLocalOnboardingCache() {
  const sp = getServerProfile()
  return typeof sp.has_consent === 'boolean' || !!sp.research_id || !!sp.has_baseline
}

export function isOnboardingFresh(ttl = TTL_MS) {
  return syncedAt > 0 && Date.now() - syncedAt < ttl
}

/**
 * @param {{ force?: boolean }} [opts]
 */
export async function ensureOnboardingSynced(opts = {}) {
  const force = !!opts.force
  if (!force && isOnboardingFresh() && hasLocalOnboardingCache()) {
    return getServerProfile()
  }
  if (inflight) return inflight

  inflight = (async () => {
    try {
      const profile = await fetchProfile()
      applyProfile(profile)
      markOnboardingSynced()
      return getServerProfile()
    } catch {
      // 网络失败时仍用本地态，避免阻断导航
      if (hasLocalOnboardingCache()) markOnboardingSynced()
      return getServerProfile()
    } finally {
      inflight = null
    }
  })()

  return inflight
}
