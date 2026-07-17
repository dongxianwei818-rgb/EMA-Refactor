import {
  getMissedDays,
  getTodayCheckinSessions,
  getVideoSkipCount,
  getVideoSkips,
  getVoiceSkipCount,
  getVoiceSkips,
} from './ema'
import { getBehaviorLogs, getBehaviorMeta } from './tracker'

function avg(arr) {
  if (!arr || !arr.length) return 0
  return Math.round(arr.reduce((s, n) => s + n, 0) / arr.length)
}

export function getBehaviorStats() {
  const logs = getBehaviorLogs()
  const meta = getBehaviorMeta()
  const byModule = {}
  logs.forEach((l) => {
    byModule[l.module] = (byModule[l.module] || 0) + 1
  })
  return {
    total: logs.length,
    byModule,
    openCount: meta.openCount || 0,
    avgDiaryWords: avg(meta.diaryWordCounts),
    avgVoiceSec: avg(meta.voiceDurations),
    avgVideoSec: avg(meta.videoDurations),
    videoSkips: getVideoSkipCount(),
    voiceSkips: getVoiceSkipCount(),
    videoSkipRecords: getVideoSkips(),
    voiceSkipRecords: getVoiceSkips(),
    missedDays: getMissedDays(),
    checkinHours: (meta.checkinTimes || []).slice(0, 7).map((c) => c.hour),
    todaySessions: getTodayCheckinSessions().length,
    recheckinCount: meta.recheckinCount || 0,
  }
}
