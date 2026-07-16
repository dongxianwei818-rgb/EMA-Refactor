import axios from 'axios'
import { CLIENT_TYPE, clearAuth, getToken } from './auth'

/** Web 管理端 API（/api/web/v1） */
const webHttp = axios.create({
  baseURL: import.meta.env.VITE_WEB_API_BASE || '/api/web/v1',
  timeout: 20000,
})

webHttp.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  config.headers['X-Client-Type'] = CLIENT_TYPE
  return config
})

webHttp.interceptors.response.use(
  (res) => {
    const body = res.data
    if (body && typeof body.code === 'number' && body.code !== 0) {
      return Promise.reject(new Error(body.message || '请求失败'))
    }
    return body?.data !== undefined ? body.data : body
  },
  (err) => {
    const status = err.response?.status
    if (status === 401) {
      clearAuth()
      if (!window.location.pathname.startsWith('/login')) {
        window.location.assign('/login')
      }
    }
    const detail = err.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : err.message
    return Promise.reject(new Error(msg || '网络错误'))
  },
)

export function fetchUsers(params = {}) {
  return webHttp.get('/users', { params })
}

export function fetchUser(userId) {
  return webHttp.get(`/users/${userId}`)
}

export function createUser(payload) {
  return webHttp.post('/users', payload)
}

export function updateUser(userId, payload) {
  return webHttp.put(`/users/${userId}`, payload)
}

export function deleteUser(userId) {
  return webHttp.delete(`/users/${userId}`)
}
