import http from './http'

export function fetchMessages(limit = 80) {
  return http.get('/chat/messages', { params: { limit } })
}

export function sendMessage(content) {
  return http.post('/chat/send', { content })
}

export function fetchFeedback(params = {}) {
  return http.get('/feedback', { params })
}

export function fetchResources() {
  return http.get('/resources')
}

export function fetchRiskAssessment() {
  return http.get('/risk/assessment')
}
