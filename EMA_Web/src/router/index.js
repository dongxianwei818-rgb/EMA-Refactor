import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import Home from '../views/Home.vue'
import Records from '../views/Records.vue'
import Trends from '../views/Trends.vue'
import Chat from '../views/Chat.vue'
import Resources from '../views/Resources.vue'
import My from '../views/My.vue'
import Users from '../views/Users.vue'
import Consent from '../views/Consent.vue'
import Login from '../views/Login.vue'
import { getToken, isAdmin } from '../api/auth'
import { fetchConsentStatus } from '../api/consent'
import { applyConsentFromServer, hasConsent } from '../utils/consentState'

const routes = [
  { path: '/login', name: 'login', component: Login, meta: { public: true } },
  {
    path: '/',
    component: MainLayout,
    redirect: '/home',
    children: [
      { path: 'home', name: 'home', component: Home, meta: { requiresAuth: true, requiresConsent: true, title: '首页' } },
      { path: 'records', name: 'records', component: Records, meta: { requiresAuth: true, requiresConsent: true, title: '记录' } },
      { path: 'trends', name: 'trends', component: Trends, meta: { requiresAuth: true, requiresConsent: true, title: '趋势' } },
      { path: 'chat', name: 'chat', component: Chat, meta: { requiresAuth: true, requiresConsent: true, title: '对话' } },
      { path: 'resources', name: 'resources', component: Resources, meta: { requiresAuth: true, requiresConsent: true, title: '资源' } },
      {
        path: 'users',
        name: 'users',
        component: Users,
        meta: { requiresAuth: true, requiresAdmin: true, title: '管理' },
      },
      { path: 'my', name: 'my', component: My, meta: { requiresAuth: true, requiresConsent: true, title: '我的' } },
    ],
  },
  { path: '/consent', name: 'consent', component: Consent, meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  if (to.name === 'login') {
    if (getToken()) {
      next({ path: '/home', replace: true })
      return
    }
    next()
    return
  }

  const needsAuth = to.meta.requiresAuth || to.meta.requiresConsent || to.meta.requiresAdmin
  if (needsAuth && !getToken()) {
    next({ path: '/login', query: { redirect: to.fullPath }, replace: true })
    return
  }

  if (to.meta.requiresAdmin && !isAdmin()) {
    next({ path: '/home', replace: true })
    return
  }

  if (!to.meta.requiresConsent || isAdmin()) {
    next()
    return
  }

  try {
    const status = await fetchConsentStatus()
    if (status.has_consent) {
      applyConsentFromServer(status)
      next()
      return
    }
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
