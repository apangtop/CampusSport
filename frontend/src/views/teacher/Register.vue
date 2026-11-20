<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">报名管理 · {{ auth.user?.class_name }}</span>
          <el-select v-model="selectedMeet" :disabled="busy" style="width:240px" @change="loadEvents">
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

      <el-alert v-if="currentMeet && !canRegister" type="warning" :closable="false" title="报名已截止，当前仅可查看报名记录" style="margin-bottom:12px" />
      <el-tabs v-model="registerMode" @tab-change="onModeChange">
        <!-- ====== 个人项目 ====== -->
        <el-tab-pane label="个人项目" name="individual">
          <el-row :gutter="16">
            <el-col :xs="24" :md="14">
              <el-form label-width="90px" size="default">
                <el-form-item label="比赛项目">
                  <el-select v-model="selectedEvent" :disabled="busy || !canRegister" style="width:100%" placeholder="选择个人项目" clearable @change="onEventSelect" v-loading="eventsLoading">
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
                        <el-checkbox :label="s.id" :disabled="busy || !canRegister || s._disabled || (selectedStudents.length >= Math.min(selectedEventInfo?.remaining || 0, 50) && !selectedStudents.includes(s.id))">
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
                :disabled="busy || !canRegister || !selectedEvent || !selectedStudents.length || selectedStudents.length > selectedEventInfo?.remaining"
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
                    <el-descriptions-item label="限报">{{ personalCap }}项/人（仅个人项目）</el-descriptions-item>
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
                        <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : row.status === 'cancelled' ? 'info' : 'warning'" size="small">
                          {{ row.status === 'approved' ? '已审核' : '待审' }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="140" align="center">
                      <template #default="{ row }">
                        <el-popconfirm v-if="canRegister" title="确认取消此报名？" @confirm="cancelReg(row)">
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
                  <el-select v-model="selectedTeamEvent" :disabled="busy || !canRegister" style="width:100%" placeholder="选择团体项目" clearable>
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
                        <el-checkbox :label="s.id" :disabled="busy || !canRegister || (teamMembers.length >= currentTeamEvent?.team_size && !teamMembers.includes(s.id))">
                          {{ s.name }} ({{ s.gender === 'male' ? '男' : '女' }})
                        </el-checkbox>
                      </div>
                    </el-checkbox-group>
                  </div>
                </el-form-item>
              </el-form>
              <el-button type="primary" :loading="teamSubmitting"
                :disabled="busy || !canRegister || teamAlreadyRegistered || !selectedTeamEvent || !currentTeamEvent?.team_size || teamMembers.length !== currentTeamEvent.team_size"
                @click="submitTeamRegister" style="width:100%">
                {{ teamAlreadyRegistered ? '本班已报名此项目' : teamEditingId ? '保存队员调整' : teamMembers.length && currentTeamEvent && teamMembers.length < currentTeamEvent.team_size ? `还需 ${currentTeamEvent.team_size - teamMembers.length} 人` : '提交团体报名' }}
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
                      <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : row.status === 'cancelled' ? 'info' : 'warning'" size="small">
                        {{ registrationStatusLabel(row.status) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="140" align="center">
                    <template #default="{ row }">
                      <el-button v-if="canRegister && isActiveRegistration(row)" link type="primary" size="small" :disabled="busy" @click="editTeam(row)">调整队员</el-button>
                      <el-popconfirm v-if="canRegister && isActiveRegistration(row)" title="确认取消此团体报名？" @confirm="cancelTeamReg(row)">
                        <template #reference>
                          <el-button link type="danger" size="small">取消</el-button>
                        </template>
                      </el-popconfirm>
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
import { useSchoolStore } from '@/stores/school'
const school = useSchoolStore()
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { meetApi, eventApi, studentApi, registrationApi, teamRegistrationApi } from '@/api'
import { extractGrade, shortDatetime } from '@/utils/format'
import { isActiveRegistration, individualCap, registrationOpen, registrationCounts, loadAllPages, registrationStatusLabel } from '@/utils/registration'

const auth = useAuthStore()
const registerMode = ref('individual')
const meets = ref([]), events = ref([]), students = ref([])
const teamRegistrations = ref([]), myRegistrations = ref([])
const selectedMeet = ref(''), selectedEvent = ref(''), selectedTeamEvent = ref('')
const selectedStudents = ref([]), teamMembers = ref([]), teamEditingId = ref(null)
const submitting = ref(false), teamSubmitting = ref(false), eventsLoading = ref(false)
const studentFilterGender = ref(''), studentFilterReg = ref('')
const now = ref(Date.now())
const timer = setInterval(() => { now.value = Date.now() }, 1000)
onUnmounted(() => clearInterval(timer))
const genderLabel = value => ({male:'男',female:'女',mixed:'混合'})[value] || value
const typeLabel = value => ({track:'径赛',field:'田赛',fun_individual:'趣味个人',relay:'接力团体',team_confrontation:'对抗团体'})[value] || value
const stageLabel = value => ({single:'直接决赛',two:'初赛+决赛',three:'三阶段'})[value] || value
const currentMeet = computed(() => meets.value.find(m => m.id === selectedMeet.value))
const canRegister = computed(() => registrationOpen(currentMeet.value, now.value))
const busy = computed(() => submitting.value || teamSubmitting.value || eventsLoading.value)
const grades = computed(() => new Set(students.value.map(s => s.grade).filter(Boolean)))
const gradeMatches = event => !event.grade || grades.value.has(event.grade) || event.grade === school.gradeForClass(auth.user?.class_name)
const individualEvents = computed(() => events.value.filter(e => !['relay','team_confrontation'].includes(e.event_type) && gradeMatches(e)))
const teamEvents = computed(() => events.value.filter(e => ['relay','team_confrontation'].includes(e.event_type) && gradeMatches(e)))
function groupEvents(items) {
  const map={}
  items.forEach(e => { (map[e.event_type] ||= {label:typeLabel(e.event_type),events:[]}).events.push(e) })
  return Object.values(map)
}
const groupedIndividualEvents = computed(() => groupEvents(individualEvents.value))
const groupedTeamEvents = computed(() => groupEvents(teamEvents.value))
const currentEventObj = computed(() => events.value.find(e => e.id === selectedEvent.value))
const currentTeamEvent = computed(() => events.value.find(e => e.id === selectedTeamEvent.value))
const selectedEventName = computed(() => currentEventObj.value?.name || '')
const counts = computed(() => registrationCounts(myRegistrations.value))
const studentRegCounts = computed(() => counts.value.students)
const classRegCounts = computed(() => counts.value.events)
const personalCap = computed(() => individualCap(currentMeet.value,currentEventObj.value))
const selectedEventInfo = computed(() => {
  const e=currentEventObj.value
  if(!e) return null
  const existing=classRegCounts.value[e.id] || 0
  return {max:e.max_per_class,existing,remaining:Math.max(0,e.max_per_class-existing)}
})
const registeredStudents = computed(() => myRegistrations.value.filter(r => r.event === selectedEvent.value && isActiveRegistration(r)))
const registeredStudentIds = computed(() => new Set(registeredStudents.value.map(r => r.student)))
const eligibleStudents = computed(() => students.value.map(s => {
  const ev=currentEventObj.value, count=studentRegCounts.value[s.id] || 0
  let reason=''
  if(!ev) reason='请先选择项目'
  else if(registeredStudentIds.value.has(s.id)) reason='已报本项目'
  else if(ev.gender!=='mixed' && s.gender!==ev.gender) reason='性别不符'
  else if(ev.grade && s.grade!==ev.grade) reason='年级不符'
  else if(count>=personalCap.value) reason=`已报${count}项，上限${personalCap.value}项`
  return {...s,_regCount:count,_disabled:!!reason,_reason:reason}
}))
const filteredEligibleStudents = computed(() => eligibleStudents.value.filter(s =>
  (!studentFilterGender.value || s.gender===studentFilterGender.value) &&
  (!studentFilterReg.value || (studentFilterReg.value==='available' ? !s._disabled :
    studentFilterReg.value==='full' ? s._disabled : s._regCount===Number(studentFilterReg.value)))
))
const filteredTeamStudents = computed(() => students.value.filter(s => {
  const e=currentTeamEvent.value
  return e && (e.gender==='mixed' || s.gender===e.gender) && (!e.grade || s.grade===e.grade)
}))
const activeTeam = computed(() => teamRegistrations.value.find(r => r.event===selectedTeamEvent.value && isActiveRegistration(r)))
const teamAlreadyRegistered = computed(() => !!activeTeam.value && activeTeam.value.id!==teamEditingId.value)

watch(selectedEvent, () => { selectedStudents.value=[] },{flush:'sync'})
watch(selectedTeamEvent, () => { teamMembers.value=[];teamEditingId.value=null },{flush:'sync'})
function onEventSelect() { selectedStudents.value=[] }
function onModeChange() {
  selectedStudents.value=[];teamMembers.value=[];selectedEvent.value='';selectedTeamEvent.value=''
}

let loadVersion=0
async function loadEvents() {
  const meetId=selectedMeet.value, version=++loadVersion
  selectedEvent.value='';selectedTeamEvent.value='';selectedStudents.value=[];teamMembers.value=[];teamEditingId.value=null
  events.value=[];myRegistrations.value=[];teamRegistrations.value=[]
  if(!meetId) return
  eventsLoading.value=true
  try {
    const params={sports_meet:meetId,class_name:auth.user?.class_name}
    const [ev,regs,teams]=await Promise.all([
      loadAllPages(eventApi.list,{sports_meet:meetId}),loadAllPages(registrationApi.list,params),loadAllPages(teamRegistrationApi.list,params)
    ])
    if(version!==loadVersion) return
    events.value=ev;myRegistrations.value=regs
    teamRegistrations.value=teams.map(t=>({...t,event_name:ev.find(e=>e.id===t.event)?.name || ''}))
  } finally { if(version===loadVersion) eventsLoading.value=false }
}
async function refreshRegistrations() {
  const meetId=selectedMeet.value, version=loadVersion
  const params={sports_meet:meetId,class_name:auth.user?.class_name}
  const [regs,teams]=await Promise.all([loadAllPages(registrationApi.list,params),loadAllPages(teamRegistrationApi.list,params)])
  if(version!==loadVersion || meetId!==selectedMeet.value) return
  myRegistrations.value=regs
  teamRegistrations.value=teams.map(t=>({...t,event_name:events.value.find(e=>e.id===t.event)?.name || ''}))
}

async function submitRegister() {
  if(busy.value || !canRegister.value || !currentEventObj.value) return
  const valid=new Set(eligibleStudents.value.filter(s=>!s._disabled).map(s=>s.id))
  const selected=[...new Set(selectedStudents.value)].filter(id=>valid.has(id))
  if(!selected.length) return ElMessage.warning('请选择可以报名的学生')
  if(selected.length>selectedEventInfo.value.remaining || selected.length>50) return ElMessage.warning('超过可报名人数或单次50人上限')
  submitting.value=true
  try {
    const res=await registrationApi.bulkRegister({event_id:selectedEvent.value,student_ids:selected})
    if(res.created?.length) ElMessage.success(`成功报名 ${res.created.length} 人：${res.created.join('、')}`)
    if(res.errors?.length) ElMessage.warning(res.errors.join('；'))
    if(res.unchanged?.length && !res.created?.length) ElMessage.info('所选学生已报名本项目')
    selectedStudents.value=[]
  } finally {
    try { await refreshRegistrations() } finally { submitting.value=false }
  }
}
async function cancelReg(row) {
  if(busy.value || !canRegister.value) return
  submitting.value=true
  try { await registrationApi.cancel(row.id);ElMessage.success('已取消报名');selectedStudents.value=[];await refreshRegistrations() }
  finally { submitting.value=false }
}
async function cancelTeamReg(row) {
  if(busy.value || !canRegister.value) return
  teamSubmitting.value=true
  try { await teamRegistrationApi.cancel(row.id);ElMessage.success('已取消团体报名');selectedTeamEvent.value='';teamMembers.value=[];await refreshRegistrations() }
  finally { teamSubmitting.value=false }
}
function editTeam(row) {
  if(busy.value || !canRegister.value) return
  selectedTeamEvent.value=row.event
  teamMembers.value=[...(row.members || [])]
  teamEditingId.value=row.id
}
async function submitTeamRegister() {
  const event=currentTeamEvent.value
  if(busy.value || !canRegister.value || !event || teamAlreadyRegistered.value) return
  const valid=new Set(filteredTeamStudents.value.map(s=>s.id))
  if(event.team_size<1) return ElMessage.warning('请联系体育老师配置每队人数')
  if(teamMembers.value.length!==event.team_size || teamMembers.value.some(id=>!valid.has(id))) return ElMessage.warning(`请选择符合要求的 ${event.team_size} 名队员`)
  teamSubmitting.value=true
  try {
    const data={event:event.id,class_name:auth.user.class_name,members:[...teamMembers.value]}
    const result = teamEditingId.value
      ? await teamRegistrationApi.update(teamEditingId.value,{members:data.members})
      : await teamRegistrationApi.create(data)
    ElMessage.success(teamEditingId.value ? result.status === 'approved' ? '队员未变更，审核状态保留' : '队员调整已保存，需重新审核' : '团体报名提交成功')
    selectedTeamEvent.value='';teamMembers.value=[];teamEditingId.value=null
  } finally { try { await refreshRegistrations() } finally { teamSubmitting.value=false } }
}

onMounted(async () => {
  await school.loadDirectory()
  const [allMeets,allStudents]=await Promise.all([loadAllPages(meetApi.list),loadAllPages(studentApi.list,{class_name:auth.user?.class_name})])
  meets.value=allMeets.filter(m=>m.status==='registration');students.value=allStudents
  selectedMeet.value=meets.value.find(m=>registrationOpen(m))?.id || meets.value[0]?.id || ''
  if(selectedMeet.value) await loadEvents()
})
</script>


<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
</style>
