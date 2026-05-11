// 从班级名提取年级，如 '2028级1班' → '2028级'
export function extractGrade(className) {
  if (!className) return ''
  const m = className.match(/^(\d{4}级)/)
  return m ? m[1] : ''
}

// 是否需要道次（只有径赛、接力、对抗需要）
export function needsLanes(eventType) {
  return ['track', 'relay', 'team_confrontation'].includes(eventType)
}

// 出场标签：道次 或 序号
export function laneLabel(eventType) {
  return needsLanes(eventType) ? '道次' : '序号'
}

// 统一时间格式化
export function shortDatetime(val) {
  if (!val) return ''
  const d = new Date(val)
  if (isNaN(d.getTime())) return val
  const M = d.getMonth() + 1
  const D = d.getDate()
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${M}/${D} ${h}:${m}`
}

export function shortDate(val) {
  if (!val) return ''
  const d = new Date(val)
  if (isNaN(d.getTime())) return val
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

export function fullDatetime(val) {
  if (!val) return ''
  const d = new Date(val)
  if (isNaN(d.getTime())) return String(val).replace('T', ' ').slice(0, 16)
  const M = String(d.getMonth() + 1).padStart(2, '0')
  const D = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${d.getFullYear()}-${M}-${D} ${h}:${m}`
}
