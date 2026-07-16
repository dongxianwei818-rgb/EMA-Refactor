import axios from 'axios'
import { CLIENT_TYPE, getToken } from './auth'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 20000,
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  config.headers['X-Client-Type'] = CLIENT_TYPE
  return config
})

http.interceptors.response.use(
  (res) => {
    const body = res.data
    if (body && typeof body.code === 'number' && body.code !== 0) {
      return Promise.reject(new Error(body.message || '请求失败'))
    }
    return body?.data !== undefined ? body.data : body
  },
  (err) => {
    const detail = err.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : err.message
    return Promise.reject(new Error(msg || '网络错误'))
  },
)

export default http
