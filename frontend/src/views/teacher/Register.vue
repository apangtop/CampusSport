<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">报名管理 · {{ auth.user?.class_name }}</span>
          <el-select v-model="selectedMeet" style="width:240px" @change="loadEvents">
            <el-option v-for="m in meets" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </div>
      </template>

      <!-- 赛事提醒 -->
      <el-alert v-if="currentMeet" type="info" :closable="false" style="margin-bottom:16px">
        <template #title>
          {{ currentMeet.name }}
          <el-tag size="small" :type="currentMeet.status === 'registration' ? 'warning' : 'info'" style="margin-left:8px">
            {{ currentMeet.status === 'registration' ? '报名中' : currentMeet.status }}
          </el-tag>
          每人限报 <strong>{{ currentMeet.max_events_per_person }}</strong> 项单项
          <span v-if="currentMeet.registration_deadline">
            · 截止：<strong>{{ shortDatetime(currentMeet.registration_deadline) }}</strong>
          </span>
        </template>
      </el-alert>

      <el-tabs v-model="registerMode" @tab-change="onModeChange">
        <!-- ====== 个人项目 ====== -->
        <el-tab-pane label="个人项目" name="individual">
          <el-row :gutter="16">
            <el-col :xs="24" :md="14">
              <el-form label-width="90px" size="default">
                <el-form-item label="比赛项目">
                  <el-select v-model="selectedEvent" style="width:100%" placeholder="选择个人项目" clearable @change="onEventSelect" v-loading="eventsLoading">
                    <el-option-group v-for="g in groupedIndividualEvents" :key="g.label" :label="g.label">
                      <el-option v-for="e in g.events" :key="e.id"
                        :label="`${e.name}（${genderLabel(e.gender)} 本班${classRegCounts[e.id] || 0}/${e.max_per_class}）`"
                        :value="e.id" />
                    </el-option-group>
                  </el-select>
                </el-form-item>
                <el-alert v-if="selectedEventInfo" :type="selectedEventInfo.remaining > 0 ? 'success' : 'error'" :closable="false" style="margin-bottom:8px">
                  本班已报 <strong>{{ selectedEventInfo.existing }}</strong> / {{ selectedEventInfo.max }} 人
                  <template v-if="selectedEventInfo.remaining > 0">
                    · 还可报 <strong>{{ selectedEventInfo.remaining }}</strong> 人
                  </template>
                  <template v-else> · 已满</template>
                </el-alert>
                <el-form-item label="筛选">
                  <div style="display:flex;gap:8px">
                    <el-select v-model="studentFilterGender" size="small" clearable placeholder="性别" style="width:80px">
                      <el-option label="男" value="male" /><el-option label="女" value="female" />
                    </el-select>
                    <el-select v-model="studentFilterReg" size="small" clearable placeholder="已报项数" style="width:100px">
                      <el-option label="未报满" value="available" />
                      <el-option label="已报1项" value="1" />
                      <el-option label="已报2项" value="2" />
                      <el-option label="已报满" value="full" />
                    </el-select>
                  </div>
                </el-form-item>
                <el-form-item label="选择学生">
                  <div style="max-height:240px;overflow-y:auto;border:1px solid #ebeef5;border-radius:6px;padding:8px">
                    <el-checkbox-group v-model="selectedStudents">
                      <div v-for="s in filteredEligibleStudents" :key="s.id" style="margin-bottom:3px;display:flex;align-items:center">
                        <el-checkbox :label="s.id" :disabled="s._disabled">
                          <span :style="s._disabled ? 'color:#c0c4cc' : ''">{{ s.name }}</span>
                        </el-checkbox>
                        <el-tag size="small" style="margin-left:4px" :type="s.gender === 'male' ? '' : 'danger'">{{ s.gender === 'male' ? '男' : '女' }}</el-tag>
                        <el-tag v-if="s._regCount > 0" size="small" type="warning" style="margin-left:4px">{{ s._regCount }}项</el-tag>
                        <span v-if="s._reason" style="margin-left:6px;font-size:11px;color:#f56c6c">{{ s._reason }}</span>
                      </div>
                    </el-checkbox-group>
                    <el-empty v-if="!eligibleStudents.length" description="请先在学生管理页添加学生" :image-size="40" />
                  </div>
                </el-form-item>
              </el-form>
              <div style="color:#909399;font-size:12px;margin-bottom:8px" v-if="selectedEvent">
                已选 <strong>{{ selectedStudents.length }}</strong> 人
                <span v-if="selectedEventInfo?.remaining > 0" style="color:#67c23a"> · 还可报 {{ selectedEventInfo.remaining }} 人</span>
                <span v-else style="color:#f56c6c"> · 已满</span>
              </div>
              <el-button type="primary" :loading="submitting"
                :disabled="!selectedEvent || !selectedStudents.length || !selectedEventInfo?.remaining"
                @click="submitRegister" style="width:100%">
                确认报名（{{ selectedStudents.length }} 人）
              </el-button>
            </el-col>
            <el-col :xs="24" :md="10">
              <div style="display:flex;flex-direction:column;gap:12px;height:100%">
                <!-- 项目详情 -->
                <el-card v-if="selectedEventInfo && selectedEvent" shadow="never" style="background:#f9fafb">
                  <el-descriptions :column="2" size="small" border>
                    <el-descriptions-item label="项目">{{ selectedEventName }}</el-descriptions-item>
                    <el-descriptions-item label="赛制">{{ stageLabel(currentEventObj?.stage_type) }}</el-descriptions-item>
                    <el-descriptions-item label="本班名额">{{ selectedEventInfo.existing }}/{{ selectedEventInfo.max }}人</el-descriptions-item>
                    <el-descriptions-item label="限报">{{ currentMeet?.max_events_per_person }}项/人</el-descriptions-item>
                  </el-descriptions>
                </el-card>

                <!-- 已报名列表 -->
                <el-card shadow="never" style="background:#f9fafb;flex:1">
                  <template #header>
                    <span v-if="selectedEvent">已报名本项目的学生（{{ registeredStudents.length }}人）</span>
                    <span v-else>选择项目查看</span>
                  </template>
                  <el-table v-if="selectedEvent && registeredStudents.length" :data="registeredStudents" size="small">
                    <el-table-column prop="student_name" label="姓名" />
                    <el-table-column label="性别" width="55" align="center">
                      <template #default="{ row }">{{ row.student_gender === 'male' ? '男' : '女' }}</template>
                    </el-table-column>
                    <el-table-column prop="lane" label="道次" width="55" align="center">
                      <template #default="{ row }">{{ row.lane || '-' }}</template>
                    </el-table-column>
                    <el-table-column prop="status" label="状态" width="80" align="center">
                      <template #default="{ row }">
                        <el-tag :type="row.status === 'approved' ? 'success' : 'warning'" size="small">
                          {{ row.status === 'approved' ? '已审核' : '待审' }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="70" align="center">
                      <template #default="{ row }">
                        <el-popconfirm title="确认取消此报名？" @confirm="cancelReg(row)">
                          <template #reference>
                            <el-button link type="danger" size="small">取消</el-button>
                          </template>
                        </el-popconfirm>
                      </template>
                    </el-table-column>
                  </el-table>
                  <el-empty v-else-if="selectedEvent" description="暂无本班报名" :image-size="50" />
                  <div v-else style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:120px">
                    <span style="color:#c0c4cc;font-size:14px">👈 请先选择比赛项目</span>
                    <el-button text size="small" style="margin-top:8px" @click="$router.push('/teacher/students')">管理学生 →</el-button>
                  </div>
                </el-card>
              </div>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- ====== 团体项目 ====== -->
        <el-tab-pane label="团体项目" name="team">
          <el-row :gutter="16">
            <el-col :xs="24" :md="12">
              <el-form label-width="90px">
                <el-form-item label="团体项目">
                  <el-select v-model="selectedTeamEvent" style="width:100%" placeholder="选择团体项目" clearable>
                    <el-option-group v-for="g in groupedTeamEvents" :key="g.label" :label="g.label">
                      <el-option v-for="e in g.events" :key="e.id"
                        :label="`${e.name}（${genderLabel(e.gender)} ${e.team_size}人/队）`"
                        :value="e.id" />
                    </el-option-group>
                  </el-select>
                </el-form-item>
                <el-alert v-if="currentTeamEvent" type="info" :closable="false" style="margin-bottom:12px">
                  每队 <strong>{{ currentTeamEvent.team_size }}</strong> 人 · 已选 <strong>{{ teamMembers.length }}</strong> 人
                </el-alert>
                <el-form-item label="选择队员">
                  <div style="max-height:250px;overflow-y:auto;border:1px solid #ebeef5;border-radius:6px;padding:8px">
                    <el-checkbox-group v-model="teamMembers">
                      <div v-for="s in filteredTeamStudents" :key="s.id" style="margin-bottom:4px">
                        <el-checkbox :label="s.id" :disabled="teamMembers.length >= currentTeamEvent?.team_size && !teamMembers.includes(s.id)">
                          {{ s.name }} ({{ s.gender === 'male' ? '男' : '女' }})
                        </el-checkbox>
                      </div>
                    </el-checkbox-group>
                  </div>
                </el-form-item>
              </el-form>
              <el-button type="primary" :loading="teamSubmitting"
                :disabled="!selectedTeamEvent || teamMembers.length !== (currentTeamEvent?.team_size || 0)"
                @click="submitTeamRegister" style="width:100%">
                {{ teamMembers.length && currentTeamEvent && teamMembers.length < currentTeamEvent.team_size ? `还需 ${currentTeamEvent.team_size - teamMembers.length} 人` : '提交团体报名' }}
              </el-button>
            </el-col>
            <el-col :xs="24" :md="12">
              <el-card shadow="never" style="background:#f9fafb">
                <template #header><span>已报团体项目</span></template>
                <div v-if="!teamRegistrations.length" style="color:#999;text-align:center;padding:20px 0">暂无</div>
                <el-table v-else :data="teamRegistrations" size="small">
                  <el-table-column label="项目">
                    <template #default="{ row }">{{ row.event_name || '团体项目' }}</template>
                  </el-table-column>
                  <el-table-column label="队员">
                    <template #default="{ row }">
                      <el-tag v-for="m in (row.members_detail || [])" :key="m.id" size="small" style="margin:1px">{{ m.name }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="status" label="状态" width="80" align="center">
                    <template #default="{ row }">
                      <el-tag :type="row.status === 'approved' ? 'success' : 'warning'" size="small">
                        {{ row.status === 'approved' ? '已通过' : '待审核' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { meetApi, eventApi, studentApi, registrationApi, teamRegistrationApi } from '@/api'
import { extractGrade, shortDatetime } from '@/utils/format'

const auth = useAuthStore()
const teacherGrade = extractGrade(auth.user?.class_name)
const registerMode = ref('individual')
const meets = ref([])
const events = ref([])
const students = ref([])
const studentRegCounts = ref({}) // student_id → 已报项数
const classRegCounts = ref({})   // event_id → 本班已报人数
const teamRegistrations = ref([])
const selectedMeet = ref('')
const selectedEvent = ref('')
const selectedTeamEvent = ref('')
const selectedStudents = ref([])
const teamMembers = ref([])
const submitting = ref(false)
const teamSubmitting = ref(false)
const eventsLoading = ref(false)
const studentFilterGender = ref('')
const studentFilterReg = ref('')
const myRegistrations = ref([])  // 本班所有报名记录

const genderMap = { male:'男', female:'女', mixed:'混合' }
const genderLabel = g => genderMap[g] || g
const typeMap = { track:'径赛', field:'田赛', relay:'接力团体' }
const typeLabel = t => typeMap[t] || t

const currentMeet = computed(() => meets.value.find(m => m.id === selectedMeet.value))

const individualEvents = computed(() => events.value.filter(e =>
  !['relay', 'team_confrontation'].includes(e.event_type) &&
  (!e.grade || e.grade === teacherGrade)
))
const teamEvents = computed(() => events.value.filter(e =>
  ['relay', 'team_confrontation'].includes(e.event_type) &&
  (!e.grade || e.grade === teacherGrade)
))

const groupedIndividualEvents = computed(() => {
  const groups = {}
  individualEvents.value.forEach(e => {
    const t = e.event_type
    if (!groups[t]) groups[t] = { label: typeLabel(t), events: [] }
    groups[t].events.push(e)
  })
  return Object.values(groups)
})
const groupedTeamEvents = computed(() => {
  const groups = {}
  teamEvents.value.forEach(e => {
    const t = e.event_type
    if (!groups[t]) groups[t] = { label: typeLabel(t), events: [] }
    groups[t].events.push(e)
  })
  return Object.values(groups)
})

const currentTeamEvent = computed(() => events.value.find(e => e.id == selectedTeamEvent.value))
const currentEventObj = computed(() => events.value.find(e => e.id === selectedEvent.value))
const selectedEventName = computed(() => currentEventObj.value?.name || '')

const selectedEventInfo = computed(() => {
  const ev = currentEventObj.value
  if (!ev) return null
  const existing = classRegCounts.value[ev.id] || 0
  return { max: ev.max_per_class, existing, remaining: Math.max(0, ev.max_per_class - existing) }
})

const stageLabel = (s) => ({ single:'直接决赛', two:'初赛+决赛', three:'三阶段' })[s] || s

const eligibleStudents = computed(() => {
  const ev = events.value.find(e => e.id === selectedEvent.value)
  const max = currentMeet.value?.max_events_per_person || 3
  return students.value.map(s => {
    const regCount = studentRegCounts.value[s.id] || 0
    const wrongGender = ev && ev.gender !== 'mixed' && s.gender !== ev.gender
    const wrongGrade = ev && ev.grade && s.grade !== ev.grade
    let reason = ''
    if (wrongGender) reason = '性别不符'
    else if (wrongGrade) reason = '年级不符'
    else if (regCount >= max) reason = `已报${regCount}项`
    return {
      ...s,
      _regCount: regCount,
      _disabled: regCount >= max || wrongGender || wrongGrade,
      _reason: reason
    }
  })
})

const filteredEligibleStudents = computed(() => {
  let list = eligibleStudents.value
  if (studentFilterGender.value) list = list.filter(s => s.gender === studentFilterGender.value)
  if (studentFilterReg.value === 'available') list = list.filter(s => !s._disabled)
  else if (studentFilterReg.value === 'full') list = list.filter(s => s._disabled)
  else if (studentFilterReg.value) list = list.filter(s => s._regCount === parseInt(studentFilterReg.value))
  return list
})

const registeredStudents = computed(() => {
  if (!selectedEvent.value) return []
  return myRegistrations.value.filter(r => r.event === selectedEvent.value && r.status !== 'cancelled')
})

const filteredTeamStudents = computed(() => {
  const ev = currentTeamEvent.value
  if (!ev) return students.value
  let list = students.value
  if (ev.gender !== 'mixed') list = list.filter(s => s.gender === ev.gender)
  if (ev.grade) list = list.filter(s => s.grade === ev.grade)
  return list
})

function onModeChange() {
  selectedStudents.value = []
  teamMembers.value = []
  selectedEvent.value = ''
  selectedTeamEvent.value = ''
  if (registerMode.value === 'team') loadTeamRegistrations()
}

async function onEventSelect() {
  selectedStudents.value = []
}

async function loadEvents() {
  if (!selectedMeet.value) return
  eventsLoading.value = true
  const [evRes, regRes] = await Promise.all([
    eventApi.list({ sports_meet: selectedMeet.value, page_size: 200 }),
    registrationApi.list({ sports_meet: selectedMeet.value, class_name: auth.user.class_name })
  ])
  events.value = evRes.results || evRes
  myRegistrations.value = regRes.results || regRes
  // 统计每个学生已报项数 + 每个项目本班已报人数
  const sCounts = {}
  const eCounts = {}
  ;(regRes.results || regRes).forEach(r => {
    if (r.status !== 'cancelled') {
      sCounts[r.student] = (sCounts[r.student] || 0) + 1
      eCounts[r.event] = (eCounts[r.event] || 0) + 1
    }
  })
  studentRegCounts.value = sCounts
  classRegCounts.value = eCounts
  eventsLoading.value = false
}

async function loadStudents() {
  const res = await studentApi.list({ class_name: auth.user.class_name, page_size: 200 })
  students.value = res.results || res
}

async function loadTeamRegistrations() {
  const params = { class_name: auth.user.class_name }
  if (selectedMeet.value) params.sports_meet = selectedMeet.value
  const res = await teamRegistrationApi.list(params)
  const data = res.results || res
  data.forEach(tr => {
    if (tr.event) tr.event_name = events.value.find(e => e.id === tr.event)?.name || ''
  })
  teamRegistrations.value = data
}

async function submitRegister() {
  if (!selectedEvent.value || !selectedStudents.value.length) return
  submitting.value = true
  try {
    const res = await registrationApi.bulkRegister({
      event_id: selectedEvent.value,
      student_ids: selectedStudents.value
    })
    const created = res.created || []
    const errors = res.errors || []
    if (created.length) ElMessage.success(`成功报名 ${created.length} 人：${created.join('、')}`)
    if (errors.length) ElMessage.warning(errors.join('；'))
    selectedStudents.value = []
    const eid = selectedEvent.value
    selectedEvent.value = ''
    await loadEvents()
    selectedEvent.value = eid
  } catch (e) {
    console.error('submitRegister error', e)
  } finally { submitting.value = false }
}

async function cancelReg(row) {
  await registrationApi.cancel(row.id)
  ElMessage.success('已取消报名')
  const eid = selectedEvent.value
  selectedEvent.value = ''
  await loadEvents()
  selectedEvent.value = eid
  selectedStudents.value = []
}

async function submitTeamRegister() {
  if (!currentTeamEvent.value) return
  if (teamMembers.value.length !== currentTeamEvent.value.team_size) {
    return ElMessage.warning(`需要选择 ${currentTeamEvent.value.team_size} 名队员`)
  }
  teamSubmitting.value = true
  try {
    await teamRegistrationApi.create({
      event: selectedTeamEvent.value,
      class_name: auth.user.class_name,
      members: teamMembers.value
    })
    ElMessage.success('团体报名提交成功')
    teamMembers.value = []
    selectedTeamEvent.value = ''
    loadTeamRegistrations()
  } finally { teamSubmitting.value = false }
}

onMounted(async () => {
  const res = await meetApi.list()
  meets.value = (res.results || res).filter(m => m.status === 'registration')
  if (meets.value.length) {
    selectedMeet.value = meets.value[0].id
    loadEvents()
  }
  loadStudents()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
</style>
