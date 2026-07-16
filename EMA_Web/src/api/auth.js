import http from './http'

const TOKEN_KEY = 'ema_chat_token'
const OPENID_KEY = 'ema_chat_openid'
const USER_ID_KEY = 'ema_chat_user_id'
export const CLIENT_TYPE = 'web'

/** 开发联调：与 EMA_WeChat OPEN_ID / MOCK_WX_LOGIN 对齐 */
const DEV_CODE = import.meta.env.VITE_MOCK_LOGIN_CODE || '0f1ffwll2gtyPh40gYml2wB0wl2ffwlv'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getOpenId() {
  return localStorage.getItem(OPENID_KEY) || ''
}

export function getUserId() {
  return localStorage.getItem(USER_ID_KEY) || ''
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(OPENID_KEY)
  localStorage.removeItem(USER_ID_KEY)
}

export async function loginWithCode(code = DEV_CODE) {
  // 绕过拦截器对未登录的依赖：直接用 axios 原始请求路径
  const { default: axios } = await import('axios')
  const base = import.meta.env.VITE_API_BASE || '/api/v1'
  const res = await axios.post(
    `${base}/auth/wx-login`,
    { code, client_type: CLIENT_TYPE },
    {
      timeout: 15000,
      headers: { 'X-Client-Type': CLIENT_TYPE },
    },
  )
  const body = res.data || {}
  const data = body.data || body
  if (!data?.token) {
    throw new Error(body.message || '登录失败')
  }
  localStorage.setItem(TOKEN_KEY, data.token)
  if (data.openid) localStorage.setItem(OPENID_KEY, data.openid)
  if (data.user_id != null) localStorage.setItem(USER_ID_KEY, String(data.user_id))
  return data
}

export async function ensureLogin() {
  if (getToken()) return { token: getToken(), openid: getOpenId() }
  return loginWithCode()
}

export async function fetchProfile() {
  return http.get('/users/me')
}
