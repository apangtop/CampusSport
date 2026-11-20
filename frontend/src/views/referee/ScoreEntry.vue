<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">成绩录入</span>
          <div style="display:flex;gap:12px">
            <el-select v-model="filterEvent" :disabled="submitting || autoSaving" placeholder="选择项目" style="width:200px" @change="loadParticipants">
              <el-option v-for="e in myEvents" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
            <el-select v-model="filterStage" :disabled="submitting || autoSaving" style="width:120px" @change="loadParticipants">
              <el-option label="决赛" value="final" />
              <el-option v-if="currentEvent?.stage_type === 'three'" label="半决赛" value="semifinal" />
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
        <el-table-column :prop="isTeam ? 'class_name' : 'student.name'" :label="isTeam ? '队伍' : '姓名'" width="100" />
        <el-table-column :prop="isTeam ? 'class_name' : 'student.class_name'" label="班级" width="120" />
        <el-table-column label="成绩" width="200">
          <template #default="{ row }">
            <el-input v-model="scoreMap[row.id]" :placeholder="`输入${unitLabel(currentEvent?.result_unit || '')}`"
              :disabled="loading || submitting || !!savingRows[row.id]" size="small" style="width:160px" @blur="autoSave(row)" />
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
        <el-button type="primary" :loading="submitting" :disabled="loading || !participants.length" @click="submitAll">
          一键提交全部成绩
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { loadAllPages } from '@/utils/registration'
import { createSaveQueue } from '@/utils/saveQueue'
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { eventApi, scoreApi, teamScoreApi } from '@/api'
import { needsLanes } from '@/utils/format'

const route = useRoute()
const myEvents = ref([])
const participants = ref([])
const loading = ref(false)
const submitting = ref(false)
const saveQueue = createSaveQueue()
const savingRows = reactive({})
const autoSaving = computed(() => Object.values(savingRows).some(count => count > 0))
const filterEvent = ref(route.query.event || '')
const filterStage = ref('final')
const scoreMap = reactive({})
const savedMap = reactive({})       // registration_id → result display
const scoreIdMap = reactive({})     // registration_id → score record id

const currentEvent = computed(() => myEvents.value.find(e => e.id == filterEvent.value))

const isTeam = computed(() => currentEvent.value?.event_type === 'relay')
const activeScoreApi = computed(() => isTeam.value ? teamScoreApi : scoreApi)
const unitMap = { second:'秒', meter:'米', count:'次', rank:'名次' }
const unitLabel = u => unitMap[u] || u

let loadVersion = 0
async function loadParticipants() {
  saveQueue.clearFailures()
  if (!filterEvent.value) { ++loadVersion; participants.value = []; loading.value = false; return }
  const version = ++loadVersion
  const event = filterEvent.value
  const stage = filterStage.value
  const team = isTeam.value
  loading.value = true
  Object.keys(scoreMap).forEach(k => delete scoreMap[k])
  Object.keys(savedMap).forEach(k => delete savedMap[k])
  Object.keys(scoreIdMap).forEach(k => delete scoreIdMap[k])
  participants.value = []
  try {
    const [res, scoresRes] = await Promise.all([
      eventApi.participants(event, { stage }),
      loadAllPages(params => (team ? teamScoreApi : scoreApi).list(params), { event, stage })
    ])
    if (version !== loadVersion) return
    participants.value = (res.results || res).filter(p => p.status === 'approved')
    ;(scoresRes.results || scoresRes).forEach(s => {
      const regId = team ? s.team_registration : s.registration
      savedMap[regId] = s.result
      scoreIdMap[regId] = s.id
      scoreMap[regId] = s.result
    })
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

async function autoSave(row) {
  if (loading.value || submitting.value) return
  const result = scoreMap[row.id]
  if (result === undefined || (String(result).trim() === '' && !scoreIdMap[row.id])) return
  const version = loadVersion
  const api = activeScoreApi.value
  const stage = filterStage.value
  const field = isTeam.value ? 'team_registration' : 'registration'
  const key = `${filterEvent.value}:${stage}:${row.id}`
  savingRows[row.id] = (savingRows[row.id] || 0) + 1
  try {
    await saveQueue.enqueue(key, async () => {
      if (savedMap[row.id] === result) return
      const numeric = Number.isFinite(Number(result)) && String(result).trim() !== '' ? Number(result) : null
      if (scoreIdMap[row.id]) await api.update(scoreIdMap[row.id], { result, result_numeric: numeric })
      else {
        const response = await api.create({ [field]: row.id, stage, result, result_numeric: numeric })
        if (version === loadVersion) scoreIdMap[row.id] = response.id
      }
      if (version === loadVersion) savedMap[row.id] = result
    })
  } catch {
    // The shared API handler displays the error; flush prevents a misleading batch success.
  } finally {
    savingRows[row.id] = Math.max(0, (savingRows[row.id] || 1) - 1)
  }
}

async function submitAll() {
  if (submitting.value || loading.value) return
  submitting.value = true
  try {
    try { await saveQueue.flush() } catch {
      ElMessage.warning('有成绩自动保存失败，请核对并重试后再提交')
      return
    }
    const scoresData = participants.value
      .filter(p => scoreMap[p.id] !== undefined && (String(scoreMap[p.id]).trim() !== '' || scoreIdMap[p.id]))
      .map(p => ({
        registration_id: p.id, stage: filterStage.value, result: scoreMap[p.id],
        result_numeric: Number.isFinite(Number(scoreMap[p.id])) && String(scoreMap[p.id]).trim() !== '' ? Number(scoreMap[p.id]) : null
      }))
    if (!scoresData.length) return ElMessage.warning('请先填写成绩')
    if (isTeam.value) await teamScoreApi.batchSubmit({ scores: scoresData.map(item => ({
      team_registration: item.registration_id, stage: item.stage, result: item.result, result_numeric: item.result_numeric
    })) })
    else await scoreApi.batchSubmit({ scores: scoresData })
    ElMessage.success(`已提交 ${scoresData.length} 条成绩，排名已自动计算`)
    await loadParticipants()
  } catch {
    // API errors are already shown by the interceptor.
  } finally { submitting.value = false }
}

watch(filterEvent, () => {
  const ev = currentEvent.value
  if (ev) {
    const allowed = ev.stage_type === 'single' ? ['final'] : ev.stage_type === 'two' ? ['preliminary', 'final'] : ['preliminary', 'semifinal', 'final']
    if (!allowed.includes(filterStage.value)) filterStage.value = allowed[0]
  }
})

onMounted(async () => {
  const res = await loadAllPages(params => eventApi.list(params))
  myEvents.value = (res.results || res).filter(e => e.event_type !== 'team_confrontation')
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
