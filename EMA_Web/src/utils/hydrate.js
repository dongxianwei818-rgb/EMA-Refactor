/**
 * 从服务端拉取用户业务数据并写入内存会话仓。
 * localStorage 仅保留登录凭证与数字人位置；业务数据一律以接口为准。
 */
import { syncPull, fetchDailyTasks } from '../api/ema'
import { applyConsentFromServer, setServerProfile, getServerProfile } from './consentState'
import {
  applyDailyTasksResponse,
  applySyncPullPayload,
  getCurrentSessionId,
  getTodayKey,
} from './ema'
import { clearLegacyBusinessStorage, getLastHydratedAt, markHydrated } from './sessionStore'

let hydratePromise = null
const HYDRATE_TTL_MS = 30 * 1000

/**
 * @param {{ force?: boolean }} [options]
 */
export async function hydrateFromServer(options = {}) {
  const force = !!options.force
  const now = Date.now()
  if (!force && hydratePromise) return hydratePromise
  if (!force && now - getLastHydratedAt() < HYDRATE_TTL_MS) return true

  hydratePromise = (async () => {
    clearLegacyBusinessStorage()

    const data = await syncPull()
    applySyncPullPayload(data)

    const sp = getServerProfile() || {}
    if (data?.research_id) {
      sp.research_id = data.research_id
      sp.has_baseline = true
    }
    if (data?.consent?.at) {
      sp.has_consent = true
      sp.consent_at = data.consent.at
      applyConsentFromServer({
        has_consent: true,
        status: 'accept',
        at: data.consent.at,
      })
    }
    if (data?.study_status) sp.study_status = data.study_status
    setServerProfile(sp)

    try {
      const sessionId = getCurrentSessionId()
      const daily = await fetchDailyTasks(getTodayKey(), sessionId)
      applyDailyTasksResponse(daily)
    } catch (err) {
      console.warn('拉取今日任务失败', err)
    }

    markHydrated()
    return data
  })()

  try {
    return await hydratePromise
  } finally {
    hydratePromise = null
  }
}

export { invalidateHydrateCache } from './sessionStore'
