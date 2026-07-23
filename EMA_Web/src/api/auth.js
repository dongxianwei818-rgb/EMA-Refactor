import axios from 'axios'
import http from './http'
import { trackEvent, flushPendingBehavior } from '../utils/tracker'
import { invalidateOnboardingGate } from '../utils/onboardingGate'
import {
  applyConsentFromServer,
  setServerProfile,
} from '../utils/consentState'
import {
  clearLegacyBusinessStorage,
  invalidateHydrateCache,
  resetStore,
} from '../utils/sessionStore'

const TOKEN_KEY = 'ema_chat_token'
const OPENID_KEY = 'ema_chat_openid'
const USER_ID_KEY = 'ema_chat_user_id'
const USER_NAME_KEY = 'ema_chat_user_name'
const ROLE_KEY = 'ema_chat_role'
export const CLIENT_TYPE = 'web'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getOpenId() {
  return localStorage.getItem(OPENID_KEY) || ''
}

export function getUserName() {
  return localStorage.getItem(USER_NAME_KEY) || getOpenId()
}

export function getUserId() {
  return localStorage.getItem(USER_ID_KEY) || ''
}

export function getRole() {
  const raw = localStorage.getItem(ROLE_KEY)
  if (raw === null || raw === '') return null
  const n = Number(raw)
  return Number.isNaN(n) ? null : n
}

/** 管理员（role=0）可跳过知情同意 */
export function isAdmin() {
  return getRole() === 0
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(OPENID_KEY)
  localStorage.removeItem(USER_ID_KEY)
  localStorage.removeItem(USER_NAME_KEY)
  localStorage.removeItem(ROLE_KEY)
  clearLegacyBusinessStorage()
  resetStore()
  invalidateHydrateCache()
  invalidateOnboardingGate()
}

function persistLogin(data) {
  if (!data?.token) {
    throw new Error('登录失败：未返回 token')
  }
  localStorage.setItem(TOKEN_KEY, data.token)
  const name = data.user_name || data.openid || ''
  if (name) {
    localStorage.setItem(OPENID_KEY, name)
    localStorage.setItem(USER_NAME_KEY, name)
  }
  if (data.user_id != null) localStorage.setItem(USER_ID_KEY, String(data.user_id))
  if (data.role != null) localStorage.setItem(ROLE_KEY, String(data.role))
  else localStorage.removeItem(ROLE_KEY)
  return data
}

/** Web 用户名密码登录 → POST /auth/login */
export async function loginWithPassword(user_name, psw) {
  const base = import.meta.env.VITE_API_BASE || '/api/v1'
  try {
    const res = await axios.post(
      `${base}/auth/login`,
      { user_name, psw, client_type: CLIENT_TYPE },
      {
        timeout: 15000,
        headers: { 'X-Client-Type': CLIENT_TYPE },
      },
    )
    const body = res.data || {}
    if (typeof body.code === 'number' && body.code !== 0) {
      throw new Error(body.message || '登录失败')
    }
    const data = body.data || body
    persistLogin(data)
    // 退出后再登录会新建参与记录：用服务端标记强制走知情同意 / 基线
    setServerProfile({
      research_id: data.research_id || null,
      has_baseline: !!data.has_baseline,
      has_consent: !!data.has_consent,
      study_status: data.study_status || null,
    })
    applyConsentFromServer({
      has_consent: !!data.has_consent,
      status: data.has_consent ? 'accept' : null,
      at: null,
    })
    clearLegacyBusinessStorage()
    resetStore()
    invalidateHydrateCache()
    invalidateOnboardingGate()
    trackEvent('auth', 'login', { user_name: data.user_name || user_name }, '/login')
    flushPendingBehavior()
    return data
  } catch (err) {
    throw normalizeAuthError(err, '登录失败')
  }
}

/** Web 登录页修改密码 → POST /auth/change-password（无需 token） */
export async function changePassword(user_name, old_psw, new_psw) {
  const base = import.meta.env.VITE_API_BASE || '/api/v1'
  try {
    const res = await axios.post(
      `${base}/auth/change-password`,
      {
        user_name,
        old_psw,
        new_psw,
        client_type: CLIENT_TYPE,
      },
      {
        timeout: 15000,
        headers: { 'X-Client-Type': CLIENT_TYPE },
      },
    )
    const body = res.data || {}
    if (typeof body.code === 'number' && body.code !== 0) {
      throw new Error(body.message || '修改密码失败')
    }
    trackEvent(
      'auth',
      'change_password',
      { user_name },
      '/login',
    )
    return body.data || body
  } catch (err) {
    throw normalizeAuthError(err, '修改密码失败')
  }
}

function normalizeAuthError(err, fallback) {
  if (err?.response) {
    const detail = err.response.data?.detail
    if (typeof detail === 'string') throw new Error(detail)
    if (Array.isArray(detail)) {
      const msg = detail.map((d) => d.msg || JSON.stringify(d)).join('；')
      throw new Error(msg || '请求参数错误')
    }
    if (typeof err.response.data?.message === 'string') {
      throw new Error(err.response.data.message)
    }
  }
  throw err instanceof Error ? err : new Error(String(err || fallback))
}

/** 已登录则返回本地会话；未登录抛错（不再自动 mock 登录） */
export async function ensureLogin() {
  if (getToken()) {
    return {
      token: getToken(),
      openid: getOpenId(),
      user_name: getUserName(),
      role: getRole(),
    }
  }
  throw new Error('未登录')
}

export async function fetchProfile() {
  return http.get('/users/me')
}

/** 写入 user_login_logs.logout_at，再清除本地登录态 */
export async function logout() {
  try {
    if (getToken()) {
      await http.post('/auth/logout-log')
    }
  } catch (e) {
    console.warn('记录登出失败', e)
  } finally {
    clearAuth()
  }
}
