<template>
  <div class="class-selector">
    <!-- 年级选择 -->
    <el-select
      v-model="selectedYear"
      placeholder="选择年级"
      :style="{ width: yearWidth }"
      @change="onYearChange"
      :clearable="clearable"
    >
      <el-option-group label="在校年级（当前届次）">
        <el-option
          v-for="y in priorityYears"
          :key="y.year"
          :label="y.label"
          :value="y.year"
        />
      </el-option-group>
      <el-option-group label="往届">
        <el-option
          v-for="y in historyYears"
          :key="y.year"
          :label="y.label"
          :value="y.year"
        />
      </el-option-group>
    </el-select>

    <!-- 班级选择 -->
    <el-select
      v-model="selectedClass"
      placeholder="选择班级"
      :style="{ width: classWidth }"
      :disabled="!selectedYear"
      @change="onClassChange"
      :clearable="clearable"
    >
      <el-option
        v-for="n in classCount"
        :key="n"
        :label="`${n}班`"
        :value="n"
      />
    </el-select>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { getGradeYears, parseClassName, currentYear } from '@/utils/classOptions'

const props = defineProps({
  modelValue: { type: String, default: '' },
  yearWidth: { type: String, default: '130px' },
  classWidth: { type: String, default: '100px' },
  classCount: { type: Number, default: 20 },
  clearable: { type: Boolean, default: true },
  yearFilter: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'change'])

const cur = currentYear()
const allYears = getGradeYears()

// 在校三届（优先）：当前年、+1、+2
const priorityYears = computed(() => {
  return [cur, cur + 1, cur + 2].map(y => ({
    year: y,
    label: gradeLabel(y)
  }))
})

// 往届
const historyYears = computed(() => {
  return [cur - 1, cur - 2, cur - 3].map(y => ({
    year: y,
    label: `${y}级（往届）`
  }))
})

function gradeLabel(year) {
  const diff = year - cur
  const gradeMap = { 0: '初三', 1: '初二', 2: '初一' }
  const gradeName = gradeMap[diff] ? `（${gradeMap[diff]}）` : ''
  return `${year}级${gradeName}`
}

const selectedYear = ref(null)
const selectedClass = ref(null)

// 解析 modelValue 初始化
watch(() => props.modelValue, (val) => {
  if (!val) {
    selectedYear.value = null
    selectedClass.value = null
    return
  }
  const parsed = parseClassName(val)
  if (parsed) {
    selectedYear.value = parsed.year
    selectedClass.value = parsed.classNum
  }
}, { immediate: true })

function onYearChange() {
  selectedClass.value = null
  if (props.yearFilter) {
    const val = `${selectedYear.value}级`
    emit('update:modelValue', val)
    emit('change', val)
  } else {
    emit('update:modelValue', '')
    emit('change', '')
  }
}

function onClassChange() {
  if (selectedYear.value && selectedClass.value) {
    const val = `${selectedYear.value}级${selectedClass.value}班`
    emit('update:modelValue', val)
    emit('change', val)
  }
}
</script>

<style scoped>
.class-selector {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
