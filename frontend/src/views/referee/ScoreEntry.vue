<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">成绩录入</span>
          <div style="display:flex;gap:12px">
            <el-select v-model="filterEvent" placeholder="选择项目" style="width:200px" @change="loadParticipants">
              <el-option v-for="e in myEvents" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
            <el-select v-model="filterStage" style="width:120px" @change="loadParticipants">
              <el-option label="决赛" value="final" />
              <el-option v-if="currentEvent && currentEvent.stage_type !== 'single'" label="初赛" value="preliminary" />
            </el-select>
          </div>
        </div>
      </template>

      <el-alert v-if="currentEvent" type="info" :closable="false" style="margin-bottom:16px">
        当前项目：<strong>{{ currentEvent.name }}</strong>，
        成绩单位：<strong>{{ unitLabel(currentEvent.result_unit) }}</strong>
      </el-alert>

      <el-table :data="participants" v-loading="loading">
        <el-table-column v-if="currentEvent" :label="needsLanes(currentEvent.event_type) ? '道次' : '序号'" width="70" align="center">
          <template #default="{ row }">{{ row.lane || '-' }}</template>
        </el-table-column>
        <el-table-column prop="student.name" label="姓名" width="100" />
        <el-table-column prop="student.class_name" label="班级" width="120" />
        <el-table-column label="成绩" width="200">
          <template #default="{ row }">
            <el-input v-model="scoreMap[row.id]" :placeholder="`输入${unitLabel(currentEvent?.result_unit || '')}`"
              size="small" style="width:160px" @blur="autoSave(row)" />
          </template>
        </el-table-column>
        <el-table-column label="已录入" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="savedMap[row.id]" type="success" size="small">
              {{ savedMap[row.id] }}
            </el-tag>
            <el-tag v-else type="info" size="small">未录入</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div style="display:flex;justify-content:flex-end;gap:12px;margin-top:16px">
        <el-button type="primary" :loading="submitting" :disabled="!participants.length" @click="submitAll">
          一键提交全部成绩
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { eventApi, scoreApi } from '@/api'
import { needsLanes } from '@/utils/format'

const route = useRoute()
const myEvents = ref([])
const participants = ref([])
const loading = ref(false)
const submitting = ref(false)
const filterEvent = ref(route.query.event || '')
const filterStage = ref('final')
const scoreMap = reactive({})
const savedMap = reactive({})       // registration_id → result display
const scoreIdMap = reactive({})     // registration_id → score record id

const currentEvent = computed(() => myEvents.value.find(e => e.id == filterEvent.value))

const unitMap = { second:'秒', meter:'米', count:'次', rank:'名次' }
const unitLabel = u => unitMap[u] || u

async function loadParticipants() {
  if (!filterEvent.value) return
  loading.value = true
  const res = await eventApi.participants(filterEvent.value)
  participants.value = res.results || res

  // 加载已有成绩（记录 score id 用于后续 update）
  const scoresRes = await scoreApi.list({ event: filterEvent.value, stage: filterStage.value, page_size: 200 })
  const scores = scoresRes.results || scoresRes
  scores.forEach(s => {
    savedMap[s.registration] = s.result
    scoreIdMap[s.registration] = s.id
    scoreMap[s.registration] = s.result
  })
  loading.value = false
}

async function autoSave(row) {
  const result = scoreMap[row.id]
  if (!result) return
  const existingId = scoreIdMap[row.id]
  if (existingId) {
    await scoreApi.update(existingId, {
      result: result,
      result_numeric: parseFloat(result) || null
    })
  } else {
    const res = await scoreApi.create({
      registration: row.id,
      stage: filterStage.value,
      result: result,
      result_numeric: parseFloat(result) || null
    })
    scoreIdMap[row.id] = res.id
  }
  savedMap[row.id] = result
}

async function submitAll() {
  const scoresData = participants.value
    .filter(p => scoreMap[p.id])
    .map(p => ({
      registration_id: p.id,
      stage: filterStage.value,
      result: scoreMap[p.id],
      result_numeric: parseFloat(scoreMap[p.id]) || null
    }))

  if (!scoresData.length) return ElMessage.warning('请先填写成绩')
  submitting.value = true
  try {
    await scoreApi.batchSubmit({ scores: scoresData })
    ElMessage.success(`已提交 ${scoresData.length} 条成绩，排名已自动计算`)
    Object.keys(scoreMap).forEach(k => {
      if (scoreMap[k]) savedMap[k] = scoreMap[k]
    })
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  const res = await eventApi.list({ page_size: 200 })
  myEvents.value = res.results || res
  if (filterEvent.value) loadParticipants()
  else if (myEvents.value.length) {
    filterEvent.value = myEvents.value[0].id
    loadParticipants()
  }
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
