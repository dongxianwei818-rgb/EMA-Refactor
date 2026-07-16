import http from './http'
import { formatClientAt } from '../utils/datetime'

function postConsentLog(path, eventInfo, clientAtMs) {
  return http.post(path, {
    event_info: eventInfo || {},
    client_at: formatClientAt(clientAtMs),
  })
}

export function fetchConsentStatus() {
  return http.get('/consent/status')
}

export function recordAcceptLog(eventInfo, clientAtMs) {
  return postConsentLog('/consent/accept-log', eventInfo, clientAtMs)
}

export function recordRevokeLog(eventInfo, clientAtMs) {
  return postConsentLog('/consent/revoke-log', eventInfo, clientAtMs)
}

export function recordExitLog(eventInfo, clientAtMs) {
  return postConsentLog('/consent/exit-log', eventInfo, clientAtMs)
}
