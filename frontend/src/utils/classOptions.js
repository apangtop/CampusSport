/**
 * 生成班级选项
 * 格式：xxxx级xx班，xxxx为毕业年份
 * 例如：2026级1班（当前初三）
 *
 * 优先显示当前年份起的3年（对应初三、初二、初一）
 * 之后附加近3年历史年份（方便历届数据筛选）
 */

const CLASS_COUNT = 20  // 每个年级最多班级数

/**
 * 获取年份列表：当前年份 +0/+1/+2，再往前 -1/-2/-3
 */
export function getGradeYears() {
  const cur = new Date().getFullYear()
  const priority = [cur, cur + 1, cur + 2]         // 现在在校三届（初三/初二/初一）
  const history = [cur - 1, cur - 2, cur - 3]       // 往届
  return [...priority, ...history]
}

/**
 * 获取某年级下所有班级选项
 * @param {number} year
 * @param {number} count 班级数量，默认20
 */
export function getClassOptions(year, count = CLASS_COUNT) {
  return Array.from({ length: count }, (_, i) => ({
    label: `${year}级${i + 1}班`,
    value: `${year}级${i + 1}班`
  }))
}

/**
 * 获取分组的班级选项（用于 el-select 分组）
 */
export function getGroupedClassOptions(count = CLASS_COUNT) {
  return getGradeYears().map(year => ({
    label: `${year}级`,
    year,
    options: getClassOptions(year, count)
  }))
}

/**
 * 从班级名称解析年级和班号
 * @param {string} className  如 "2026级3班"
 * @returns {{ year: number, classNum: number } | null}
 */
export function parseClassName(className) {
  const match = className?.match(/^(\d{4})级(\d+)班$/)
  if (!match) return null
  return { year: parseInt(match[1]), classNum: parseInt(match[2]) }
}

/**
 * 获取当前年份
 */
export function currentYear() {
  return new Date().getFullYear()
}
