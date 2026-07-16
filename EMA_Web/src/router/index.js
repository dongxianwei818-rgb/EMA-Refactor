import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Chat from '../views/Chat.vue'
import Resources from '../views/Resources.vue'
import Consent from '../views/Consent.vue'
import { ensureLogin, getToken } from '../api/auth'
import { fetchConsentStatus } from '../api/consent'
import { applyConsentFromServer, hasConsent } from '../utils/consentState'

const routes = [
  { path: '/', name: 'home', component: Home, meta: { requiresConsent: true } },
  { path: '/chat', name: 'chat', component: Chat, meta: { requiresConsent: true } },
  { path: '/resources', name: 'resources', component: Resources, meta: { requiresConsent: true } },
  { path: '/consent', name: 'consent', component: Consent },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  // 知情同意页本身不强制拦截
  if (to.name === 'consent') {
    next()
    return
  }

  if (!to.meta.requiresConsent) {
    next()
    return
  }

  try {
    if (!getToken()) await ensureLogin()
    const status = await fetchConsentStatus()
    if (status.has_consent) {
      applyConsentFromServer(status)
      next()
      return
    }
    // 本地刚同意、服务端流水尚未落库时，避免被 status=false 清掉本地并打回授权页
    if (hasConsent()) {
      next()
      return
    }
    applyConsentFromServer(status)
    next({ path: '/consent', replace: true })
    return
  } catch {
    if (!hasConsent()) {
      next({ path: '/consent', replace: true })
      return
    }
  }
  next()
})

export default router
