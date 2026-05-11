<template>
  <div>
    <el-page-header content="报名审核" @back="$router.push(`/admin/meets/${meetId}`)" style="margin-bottom:20px" />
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
            <el-select v-model="filterStatus" placeholder="筛选状态" clearable style="width:110px">
              <el-option label="未审核" value="submitted" />
              <el-option label="已审核" value="approved" />
              <el-option label="已拒绝" value="rejected" />
            </el-select>
            <el-select v-model="filterType" placeholder="项目分类" clearable style="width:100px">
              <el-option label="全部" value="" />
              <el-option v-if="availTypes.has('track')" label="径赛" value="track" />
              <el-option v-if="availTypes.has('field')" label="田赛" value="field" />
              <el-option v-if="availTypes.has('relay')" label="接力" value="relay" />
            </el-select>
            <ClassSelector v-model="filterClass" :clearable="true" :year-filter="true" />
            <el-select v-model="filterEvent" placeholder="筛选项目" clearable style="width:200px" @change="load">
              <el-option v-for="e in filteredEvents" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
          </div>
          <div style="display:flex;gap:8px">
            <el-button type="success" @click="approveAll">一键审核全部</el-button>
            <el-button type="warning" @click="autoAssign" :disabled="!filterEvent">自动分组道次</el-button>
          </div>
        </div>
      </template>
      <el-table :data="registrations" v-loading="loading" @selection-change="selection = $event">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="student_name" label="学生姓名" width="100" />
        <el-table-column prop="student_class" label="班级" width="110" />
        <el-table-column prop="event_name" label="报名项目" min-width="130" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="道次/序号" width="75" align="center">
          <template #default="{ row }">
            <el-input v-if="eventNeedsLane(row.event)" v-model="laneEdits[row.id]" size="small" style="width:55px"
              @change="val => updateLane(row.id, val)" />
            <span v-else style="color:#ccc;font-size:12px">-</span>
          </template>
        </el-table-column>
        <el-table-column label="报名时间" width="140">
          <template #default="{ row }">{{ shortDatetime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center">
          <template #default="{ row }">
            <el-button v-if="row.status === 'submitted'" link type="success" @click="approve(row)">审核</el-button>
            <el-button v-if="row.status === 'submitted'" link type="danger" @click="reject(row)">拒绝</el-button>
            <el-button link type="danger" @click="deleteReg(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { registrationApi, eventApi } from '@/api'
import { shortDatetime, needsLanes } from '@/utils/format'

function eventNeedsLane(eventId) {
  const ev = events.value.find(e => e.id === eventId)
  return ev ? needsLanes(ev.event_type) : true
}
import ClassSelector from '@/components/ClassSelector.vue'

const route = useRoute()
const meetId = route.params.id
const registrations = ref([])
const events = ref([])
const selection = ref([])
const loading = ref(false)
const filterEvent = ref('')
const filterStatus = ref('')
const filterType = ref('')
const filterClass = ref('')

const filteredEvents = computed(() => {
  let list = events.value
  if (filterType.value) list = list.filter(e => e.event_type === filterType.value)
  if (filterClass.value && filterClass.value.endsWith('级')) {
    list = list.filter(e => e.grade === filterClass.value)
  }
  return list
})

const availTypes = computed(() => {
  const s = new Set()
  events.value.forEach(e => s.add(e.event_type))
  return s
})

const laneEdits = reactive({})

const statusMap = { submitted:'未审核', approved:'已审核', rejected:'已拒绝', cancelled:'已取消' }
const statusTypeMap = { submitted:'danger', approved:'success', rejected:'warning', cancelled:'info' }
const statusLabel = s => statusMap[s] || s
const statusType = s => statusTypeMap[s] || ''

async function updateLane(regId, val) {
  await registrationApi.update(regId, { lane: val ? parseInt(val) : null })
}

async function reloadEvents() {
  const params = { sports_meet: meetId }
  if (filterStatus.value) params.reg_status = filterStatus.value
  if (filterType.value) params.type = filterType.value
  try {
    const evRes = await eventApi.list(params)
    events.value = evRes.results || evRes
  } catch {}
}

watch([filterStatus, filterType, filterClass], async () => {
  filterEvent.value = ''
  try {
    await reloadEvents()
  } catch {}
  load()
})

async function load() {
  loading.value = true
  try {
    const params = { sports_meet: meetId }
    if (filterEvent.value) params.event = filterEvent.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterClass.value) params.class_name = filterClass.value
    const res = await registrationApi.list(params)
    registrations.value = res.results || res
    registrations.value.forEach(r => { laneEdits[r.id] = r.lane || '' })
  } catch {}
  loading.value = false
}

async function approve(row) {
  await registrationApi.approve(row.id)
  ElMessage.success('审核通过')
  load()
}

async function reject(row) {
  await registrationApi.reject(row.id)
  ElMessage.success('已拒绝')
  load()
}

async function approveAll() {
  await ElMessageBox.confirm('确认审核所有已提交的报名？', '提示', { type: 'warning' })
  const params = {}
  if (filterEvent.value) params.event_id = filterEvent.value
  const res = await registrationApi.approveAll(params)
  ElMessage.success(res.detail)
  load()
}

async function autoAssign() {
  try {
    const ev = events.value.find(e => e.id == filterEvent.value)
    const isTrack = ev && needsLanes(ev.event_type)
    let lanes = 0
    if (isTrack) {
      const result = await ElMessageBox.prompt('每组几道？', '自动分组', {
        confirmButtonText: '确定',
        inputValue: '6',
        inputPattern: /^\d+$/,
        inputErrorMessage: '请输入数字'
      })
      lanes = parseInt(result.value) || 8
    }
    const res = await eventApi.autoAssignLanes(filterEvent.value, { lanes_per_group: lanes || 999 })
    ElMessage.success(res.detail)
    load()
  } catch {}
}

async function deleteReg(row) {
  await ElMessageBox.confirm('确认删除此报名？', '提示', { type: 'warning' })
  await registrationApi.delete(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(async () => {
  const res = await eventApi.list({ sports_meet: meetId, page_size: 200 })
  events.value = res.results || res
  load()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
