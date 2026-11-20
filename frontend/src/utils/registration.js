export const isActiveRegistration = record => ['submitted', 'approved'].includes(record.status)

export function individualCap(meet, event) {
  const meetCap = meet?.max_events_per_person ?? 3
  return Math.min(meetCap, event?.max_per_person || meetCap)
}

export function registrationOpen(meet, now = Date.now()) {
  if (!meet || meet.status !== 'registration') return false
  if (!meet.registration_deadline) return true
  const deadline = Date.parse(meet.registration_deadline)
  return Number.isFinite(deadline) && now < deadline
}

export function registrationCounts(records) {
  const students = {}, events = {}
  for (const record of records) {
    if (!isActiveRegistration(record)) continue
    students[record.student] = (students[record.student] || 0) + 1
    events[record.event] = (events[record.event] || 0) + 1
  }
  return { students, events }
}

// Follow page numbers through the existing API method; never follow an arbitrary next URL.
export async function loadAllPages(list, params = {}) {
  const records = []
  for (let page = 1; page <= 1000; page++) {
    const res = await list({ ...params, page, page_size: 2000 })
    if (Array.isArray(res)) return res
    if (!res || !Array.isArray(res.results)) throw new Error('列表响应格式错误')
    records.push(...res.results)
    if (!res.next) return records
    if (!res.results.length) throw new Error('分页响应异常，请刷新重试')
  }
  throw new Error('数据页数过多，请缩小查询范围')
}

export const registrationStatusLabel = status => ({
  submitted: '待审核', approved: '已审核', rejected: '已拒绝', cancelled: '已取消'
})[status] || status
