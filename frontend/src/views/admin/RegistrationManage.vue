<template>
  <div>
    <el-page-header content="报名审核" @back="$router.push(`/admin/meets/${meetId}`)" style="margin-bottom:20px" />
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
            <el-radio-group v-model="regMode" size="small" @change="onModeChange">
              <el-radio-button label="individual">个人项目</el-radio-button>
              <el-radio-button label="team">团体项目</el-radio-button>
            </el-radio-group>
            <el-select v-model="filterStatus" placeholder="筛选状态" clearable style="width:110px">
              <el-option label="未审核" value="submitted" />
              <el-option label="已审核" value="approved" />
              <el-option label="已拒绝" value="rejected" />
            </el-select>
            <el-select v-if="regMode === 'individual'" v-model="filterType" placeholder="项目分类" clearable style="width:100px" @change="onFilterTypeChange">
              <el-option label="全部" value="" />
              <el-option v-if="availTypes.has('track')" label="径赛" value="track" />
              <el-option v-if="availTypes.has('field')" label="田赛" value="field" />
            </el-select>
            <ClassSelector v-model="filterClass" :clearable="true" :year-filter="true" />
            <el-select v-model="filterEvent" placeholder="筛选项目" clearable style="width:200px" @change="load">
              <el-option v-for="e in filteredEvents" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
            <el-button @click="resetFilter">重置筛选</el-button>
          </div>
          <div style="display:flex;gap:8px">
            <el-button type="success" @click="approveAll">一键审核全部</el-button>
            <el-button type="warning" @click="autoAssign" :disabled="!filterEvent || !canAutoAssign">自动分组道次</el-button>
          </div>
        </div>
      </template>

      <!-- 个人项目报名 -->
      <template v-if="regMode === 'individual'">
        <el-table :data="registrations" v-loading="loading">
          <el-table-column label="#" width="45" align="center">
            <template #default="{ $index }">{{ (page - 1) * pageSize + $index + 1 }}</template>
          </el-table-column>
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
        <div class="pagination-bar">
          <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
            layout="total, prev, pager, next" @current-change="onPageChange" size="small" background />
        </div>
      </template>

      <!-- 团体项目报名 -->
      <template v-else>
        <el-table :data="teamRegs" v-loading="loading">
          <el-table-column label="#" width="45" align="center">
            <template #default="{ $index }">{{ (teamPage - 1) * teamPageSize + $index + 1 }}</template>
          </el-table-column>
          <el-table-column prop="class_name" label="班级" width="120" />
          <el-table-column label="比赛项目" min-width="160">
            <template #default="{ row }">{{ teamEventName(row.event) }}</template>
          </el-table-column>
          <el-table-column label="队员" min-width="200">
            <template #default="{ row }">
              <el-tag v-for="m in (row.members_detail || [])" :key="m.id" size="small" style="margin:1px">{{ m.name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'submitted' ? 'danger' : row.status === 'approved' ? 'success' : 'warning'" size="small">
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="报名时间" width="140">
            <template #default="{ row }">{{ shortDatetime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" align="center">
            <template #default="{ row }">
              <el-button v-if="row.status === 'submitted'" link type="success" @click="approveTeam(row)">审核</el-button>
              <el-button v-if="row.status === 'submitted'" link type="danger" @click="rejectTeam(row)">拒绝</el-button>
              <el-button link type="danger" @click="deleteTeam(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-bar">
          <el-pagination v-model:current-page="teamPage" :page-size="teamPageSize" :total="teamTotal"
            layout="total, prev, pager, next" @current-change="onTeamPageChange" size="small" background />
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { registrationApi, teamRegistrationApi, eventApi } from '@/api'
import { shortDatetime, needsLanes } from '@/utils/format'

import ClassSelector from '@/components/ClassSelector.vue'

const route = useRoute()
const meetId = route.params.id
const regMode = ref('individual')
const registrations = ref([])
const teamRegs = ref([])
const events = ref([])
const loading = ref(false)
const filterEvent = ref('')
const filterStatus = ref('')
const filterType = ref('')
const filterClass = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const teamPage = ref(1)
const teamPageSize = ref(10)
const teamTotal = ref(0)

const filteredEvents = computed(() => {
  let list = events.value
  if (regMode.value === 'team') {
    list = list.filter(e => ['relay', 'team_confrontation'].includes(e.event_type))
  } else if (filterType.value) {
    list = list.filter(e => e.event_type === filterType.value)
  }
  if (filterClass.value && filterClass.value.endsWith('级')) {
    list = list.filter(e => e.grade === filterClass.value)
  }
  return list
})

const canAutoAssign = computed(() => {
  return !!filterEvent.value
})

const availTypes = computed(() => {
  const s = new Set()
  events.value.forEach(e => {
    if (!['relay', 'team_confrontation'].includes(e.event_type)) s.add(e.event_type)
  })
  return s
})

const laneEdits = reactive({})

const statusMap = { submitted:'未审核', approved:'已审核', rejected:'已拒绝', cancelled:'已取消' }
const statusTypeMap = { submitted:'danger', approved:'success', rejected:'warning', cancelled:'info' }
const statusLabel = s => statusMap[s] || s
const statusType = s => statusTypeMap[s] || ''

function teamEventName(eventId) {
  return events.value.find(e => e.id === eventId)?.name || ''
}

function eventNeedsLane(eventId) {
  const ev = events.value.find(e => e.id === eventId)
  return ev ? needsLanes(ev.event_type) : true
}

function onModeChange() {
  filterEvent.value = ''
  filterType.value = ''
  load()
}

function onFilterTypeChange() {
  filterEvent.value = ''
  page.value = 1
  load()
}

function onPageChange() { load() }
function onTeamPageChange() { load() }

function resetFilter() {
  filterEvent.value = ''
  filterStatus.value = ''
  filterType.value = ''
  filterClass.value = ''
  page.value = 1
  teamPage.value = 1
  load()
}

async function updateLane(regId, val) {
  await registrationApi.update(regId, { lane: val ? parseInt(val) : null })
}

watch([filterStatus, filterClass], () => {
  filterEvent.value = ''
  page.value = 1
  teamPage.value = 1
  load()
})

async function load() {
  loading.value = true
  try {
    if (regMode.value === 'team') {
      const params = { sports_meet: meetId, page: teamPage.value, page_size: teamPageSize.value }
      if (filterEvent.value) params.event = filterEvent.value
      if (filterStatus.value) params.status = filterStatus.value
      if (filterClass.value) params.class_name = filterClass.value
      const res = await teamRegistrationApi.list(params)
      teamRegs.value = res.results || res
      teamTotal.value = res.count || 0
    } else {
      const params = { sports_meet: meetId, page: page.value, page_size: pageSize.value }
      if (filterEvent.value) params.event = filterEvent.value
      if (filterStatus.value) params.status = filterStatus.value
      if (filterClass.value) params.class_name = filterClass.value
      if (filterType.value) params.type = filterType.value
      const res = await registrationApi.list(params)
      registrations.value = res.results || res
      total.value = res.count || 0
      registrations.value.forEach(r => { laneEdits[r.id] = r.lane || '' })
    }
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
  await ElMessageBox.confirm(
    regMode.value === 'team' ? '确认审核所有团体项目已提交的报名？' : '确认审核所有已提交的报名？',
    '提示', { type: 'warning' }
  )
  if (regMode.value === 'team') {
    const params = {}
    if (filterEvent.value) params.event_id = filterEvent.value
    const res = await teamRegistrationApi.approveAll(params)
    ElMessage.success(res.detail)
  } else {
    const params = {}
    if (filterEvent.value) params.event_id = filterEvent.value
    const res = await registrationApi.approveAll(params)
    ElMessage.success(res.detail)
  }
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

async function approveTeam(row) {
  await teamRegistrationApi.approve(row.id)
  ElMessage.success('审核通过')
  load()
}

async function rejectTeam(row) {
  await teamRegistrationApi.reject(row.id)
  ElMessage.success('已拒绝')
  load()
}

async function deleteTeam(row) {
  await ElMessageBox.confirm('确认删除此团体报名？', '提示', { type: 'warning' })
  await teamRegistrationApi.delete(row.id)
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
.card-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.pagination-bar { display: flex; justify-content: flex-end; margin-top: 12px; }
</style>
