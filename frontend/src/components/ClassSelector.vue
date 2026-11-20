<template>
  <div class="class-selector">
    <el-select v-model="selectedGrade" aria-label="选择年级" placeholder="选择年级" :style="{ width: yearWidth }"
      :clearable="clearable" filterable @change="onGradeChange">
      <el-option v-for="grade in grades" :key="grade" :label="grade" :value="grade" />
    </el-select>
    <el-select :model-value="classValue" aria-label="选择班级" placeholder="选择或输入班级" :style="{ width: classWidth }"
      :clearable="clearable" filterable allow-create default-first-option @change="onClassChange">
      <el-option v-for="item in classes" :key="item.name" :label="item.name" :value="item.name" />
    </el-select>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, nextTick } from 'vue'
import { useSchoolStore } from '@/stores/school'
import { getGradeYears, getClassOptions } from '@/utils/classOptions'
const props = defineProps({
  modelValue: { type: String, default: '' },
  yearWidth: { type: String, default: '130px' },
  classWidth: { type: String, default: '150px' },
  classCount: { type: Number, default: 20 },
  clearable: { type: Boolean, default: true },
  yearFilter: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue', 'change'])
const school = useSchoolStore()
const selectedGrade = ref('')
const grades = computed(() => [...new Set([...(school.grades.length ? school.grades : getGradeYears().map(year => `${year}级`)), selectedGrade.value].filter(Boolean))])
const classValue = computed(() => school.isGrade(props.modelValue) ? '' : props.modelValue)
const classes = computed(() => {
  const source = school.classes.length ? school.classes : getGradeYears().flatMap(year => getClassOptions(year, props.classCount).map(item => ({ name: item.value, grade: `${year}级` })))
  return source.filter(item => !selectedGrade.value || item.grade === selectedGrade.value)
})
watch(() => [props.modelValue, school.classes, school.grades], () => {
  selectedGrade.value = school.isGrade(props.modelValue) ? props.modelValue : school.gradeForClass(props.modelValue)
}, { immediate: true })
function publish(value) { emit('update:modelValue', value || ''); emit('change', value || '') }
async function onGradeChange(value) {
  publish(props.yearFilter ? value : '')
  await nextTick()
  selectedGrade.value = value || ''
}
function onClassChange(value) { publish(value) }
onMounted(() => school.loadDirectory().catch(() => {}))
</script>

<style scoped>
.class-selector { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
</style>
