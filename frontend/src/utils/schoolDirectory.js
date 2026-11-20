export function gradeForClass(classes, name) {
  return classes.find(item => item.name === name)?.grade || name?.match(/^(\d{4}级)/)?.[1] || ''
}

export function parseSchoolClasses(text) {
  const rows = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
  if (rows.length > 2000) throw new Error('班级不能超过 2000 个')
  const names = new Set()
  return rows.map((line, index) => {
    const parts = line.split('|').map(value => value.trim())
    if (parts.length !== 2 || !parts[0] || !parts[1]) throw new Error(`第 ${index + 1} 行请填写“班级名称 | 年级名称”`)
    const [name, grade] = parts
    if (name.length > 50 || grade.length > 20) throw new Error(`第 ${index + 1} 行班级或年级名称过长`)
    if (names.has(name)) throw new Error(`班级「${name}」重复`)
    names.add(name)
    return { name, grade }
  })
}
