import { getBehaviorStats } from './behaviorStats'
import { getBehaviorLogs, getBehaviorMeta } from './tracker'

const MODULE_LABELS = {
  app: '应用',
  home: '首页',
  my: '我的',
  records: '记录',
  trends: '趋势',
  resources: '资源',
  consent: '知情同意',
  baseline: '基线测评',
  questionnaire: 'EMA 问卷',
  diary: '文本日记',
  voice: '语音',
  video: '视频',
  steps: '步数',
  checkin: '打卡',
}

function formatDateTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const pad = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function pushRows(rows, label, value) {
  if (value === undefined || value === null || value === '') return
  rows.push({ label, value: String(value) })
}

function moduleLabel(module) {
  return MODULE_LABELS[module] || module || '未知'
}

export function buildBehaviorDetailSections() {
  const stats = getBehaviorStats()
  const meta = getBehaviorMeta()
  const logs = getBehaviorLogs()
  const sections = []

  const summaryRows = []
  pushRows(summaryRows, '行为记录总数', stats.total)
  pushRows(summaryRows, '打开次数', stats.openCount)
  pushRows(summaryRows, '今日已完成打卡轮次', stats.todaySessions)
  pushRows(summaryRows, '连续缺测天数', stats.missedDays)
  pushRows(summaryRows, '补打卡次数', stats.recheckinCount)
  pushRows(summaryRows, '平均日记字数', stats.avgDiaryWords)
  pushRows(summaryRows, '平均语音时长(秒)', stats.avgVoiceSec)
  pushRows(summaryRows, '平均视频时长(秒)', stats.avgVideoSec)
  pushRows(summaryRows, '语音跳过次数', stats.voiceSkips)
  pushRows(summaryRows, '视频跳过次数', stats.videoSkips)
  if (summaryRows.length) {
    sections.push({ id: 'summary', title: '行为概览', rows: summaryRows })
  }

  const moduleKeys = Object.keys(stats.byModule || {})
  if (moduleKeys.length) {
    moduleKeys.sort((a, b) => stats.byModule[b] - stats.byModule[a])
    sections.push({
      id: 'byModule',
      title: '模块行为统计',
      rows: moduleKeys.map((key) => ({
        label: moduleLabel(key),
        value: `${stats.byModule[key]} 次`,
      })),
    })
  }

  const checkinRows = []
  ;(meta.checkinTimes || []).forEach((item, index) => {
    pushRows(
      checkinRows,
      `问卷提交 ${index + 1}`,
      `${formatDateTime(item.at)}（${item.hour} 时，第 ${item.sessionId || 1} 轮）`,
    )
  })
  ;(meta.checkinSessions || []).forEach((item, index) => {
    pushRows(
      checkinRows,
      `完成轮次 ${index + 1}`,
      `${formatDateTime(item.at)}${item.date ? `（${item.date}）` : ''}`,
    )
  })
  if (checkinRows.length) {
    sections.push({ id: 'checkin', title: '打卡行为', rows: checkinRows })
  }

  const diaryRows = []
  ;(meta.diaryWordCounts || []).forEach((count, index) => {
    pushRows(diaryRows, `日记 ${index + 1}`, `${count} 字`)
  })
  if (diaryRows.length) {
    sections.push({ id: 'diary', title: '日记行为', rows: diaryRows })
  }

  const voiceRows = []
  ;(meta.voiceDurations || []).forEach((sec, index) => {
    pushRows(voiceRows, `录音 ${index + 1}`, `${sec} 秒`)
  })
  ;(stats.voiceSkipRecords || []).forEach((item, index) => {
    pushRows(voiceRows, `跳过记录 ${index + 1}`, formatDateTime(item.at || item))
  })
  if (voiceRows.length) {
    sections.push({ id: 'voice', title: '语音行为', rows: voiceRows })
  }

  const videoRows = []
  ;(meta.videoDurations || []).forEach((sec, index) => {
    pushRows(videoRows, `录制 ${index + 1}`, `${sec} 秒`)
  })
  ;(stats.videoSkipRecords || []).forEach((item, index) => {
    pushRows(videoRows, `跳过记录 ${index + 1}`, formatDateTime(item.at || item))
  })
  if (videoRows.length) {
    sections.push({ id: 'video', title: '视频行为', rows: videoRows })
  }

  const taskRows = []
  ;(meta.taskDurations || []).forEach((item, index) => {
    const ms = item && item.ms != null ? item.ms : item
    const route = item && item.route ? `（${item.route}）` : ''
    const sec = typeof ms === 'number' ? Math.round(ms / 100) / 10 : ms
    pushRows(taskRows, `任务 ${index + 1}`, `${sec} 秒${route}`)
  })
  if (taskRows.length) {
    sections.push({ id: 'task', title: '任务耗时', rows: taskRows })
  }

  return {
    sections,
    logs: logs.map((log, index) => ({
      id: index,
      time: formatDateTime(log.at),
      summary: `${moduleLabel(log.module)} · ${log.action || ''}`,
    })),
  }
}
