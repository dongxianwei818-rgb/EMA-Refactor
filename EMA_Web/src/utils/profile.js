import { BASELINE_SECTIONS } from '../constants/ema'

export function formatBaselineTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
}

function collectSectionRows(section, profile) {
  const rows = []
  if (section.fields) {
    section.fields.forEach((f) => {
      const val = profile[f.id]
      if (val !== undefined && val !== null && val !== '') {
        rows.push({ id: f.id, label: f.label, value: val })
      }
    })
  }
  if (section.items) {
    section.items.forEach((q) => {
      const val = profile[q.id]
      if (val !== undefined && val !== null && val !== '') {
        rows.push({ id: q.id, label: q.label, value: val })
      }
    })
  }
  return rows
}

/** 「我的」页摘要：研究编号 + 年龄/年级等基本信息 */
export function buildBasicSummary(profile) {
  const section = BASELINE_SECTIONS.find((s) => s.id === 'basic')
  if (!section?.fields) return []
  const order = ['researchId', 'age', 'grade', 'major', 'gender', 'onlyChild', 'housing']
  const byId = Object.fromEntries(section.fields.map((f) => [f.id, f]))
  const normalized = {
    ...profile,
    researchId: profile.researchId || profile.research_id || '',
  }
  const rows = []
  order.forEach((id) => {
    const field = byId[id]
    if (!field) return
    const val = normalized[id]
    if (val !== undefined && val !== null && val !== '') {
      rows.push({ id, label: field.label, value: val })
    }
  })
  return rows
}

/** 详情页：按小程序顺序展示全部已填写的基线分节 */
export function buildProfileDetailSections(profile) {
  const sections = []
  const normalized = {
    ...profile,
    researchId: profile.researchId || profile.research_id || '',
  }
  BASELINE_SECTIONS.forEach((section) => {
    const rows = collectSectionRows(section, normalized)
    if (rows.length) {
      sections.push({ id: section.id, title: section.title, rows })
    }
  })
  return sections
}
