<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <span style="font-size:16px;font-weight:600">为本班学生报名</span>
      </template>

      <el-tabs v-model="registerMode" @tab-change="onModeChange">
        <!-- ====== 个人项目报名 ====== -->
        <el-tab-pane label="个人项目" name="individual">
          <el-row :gutter="20">
            <el-col :span="10">
              <el-form label-width="80px">
                <el-form-item label="运动会">
                  <el-select v-model="selectedMeet" style="width:100%" @change="loadEvents">
                    <el-option v-for="m in meets" :key="m.id" :label="m.name" :value="m.id" />
                  </el-select>
                </el-form-item>
                <el-alert v-if="currentMeet" type="info" :closable="false" style="margin-bottom:12px">
                  每位学生最多报名 <strong>{{ currentMeet.max_events_per_person }}</strong> 个项目
                </el-alert>
                <el-form-item label="比赛项目">
                  <el-select v-model="selectedEvent" style="width:100%" placeholder="选择个人项目" clearable>
                    <el-option v-for="e in individualEvents" :key="e.id"
                      :label="`${e.name}（${genderLabel(e.gender)}，班级上限${e.max_per_class}人）`"
                      :value="e.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="选择学生">
                  <el-checkbox-group v-model="selectedStudents">
                    <div v-for="s in students" :key="s.id" style="margin-bottom:6px">
                      <el-checkbox :label="s.id">{{ s.name }} ({{ s.gender === 'male' ? '男' : '女' }})</el-checkbox>
                    </div>
                  </el-checkbox-group>
                </el-form-item>
              </el-form>
              <el-button type="primary" :loading="submitting" :disabled="!selectedEvent || !selectedStudents.length"
                @click="submitRegister" style="width:100%">
                提交报名（{{ selectedStudents.length }} 人）
              </el-button>
            </el-col>
            <el-col :span="14">
              <el-card shadow="never" style="background:#f9fafb">
                <template #header><span>学生管理 - {{ auth.user?.class_name }}</span></template>
                <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
                  <el-input v-model="newStudent.name" placeholder="姓名" style="width:90px" />
                  <el-select v-model="newStudent.gender" style="width:75px">
                    <el-option label="男" value="male" />
                    <el-option label="女" value="female" />
                  </el-select>
                  <el-input v-model="newStudent.student_id" placeholder="学号(可选)" style="width:110px" />
                  <el-button type="primary" @click="addStudent">添加</el-button>
                </div>
                <el-table :data="students" size="small">
                  <el-table-column prop="name" label="姓名" width="90" />
                  <el-table-column prop="gender" label="性别" width="60" align="center">
                    <template #default="{ row }">{{ row.gender === 'male' ? '男' : '女' }}</template>
                  </el-table-column>
                  <el-table-column prop="student_id" label="学号" />
                  <el-table-column label="操作" width="70" align="center">
                    <template #default="{ row }">
                      <el-button link type="danger" size="small" @click="deleteStudent(row)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- ====== 团体项目报名 ====== -->
        <el-tab-pane label="团体项目" name="team">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form label-width="80px">
                <el-form-item label="运动会">
                  <el-select v-model="selectedMeet" style="width:100%" @change="loadEvents">
                    <el-option v-for="m in meets" :key="m.id" :label="m.name" :value="m.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="团体项目">
                  <el-select v-model="selectedTeamEvent" style="width:100%" placeholder="选择团体项目" clearable>
                    <el-option v-for="e in teamEvents" :key="e.id"
                      :label="`${e.name}（${genderLabel(e.gender)}，${e.team_size}人/队，班级限${e.max_per_class}队）`"
                      :value="e.id" />
                  </el-select>
                </el-form-item>
                <el-alert v-if="currentTeamEvent" type="info" :closable="false" style="margin-bottom:12px">
                  每队需 <strong>{{ currentTeamEvent.team_size }}</strong> 人，已选 <strong>{{ teamMembers.length }}</strong> 人
                </el-alert>
                <el-form-item label="选择队员">
                  <el-checkbox-group v-model="teamMembers">
                    <div v-for="s in filteredTeamStudents" :key="s.id" style="margin-bottom:6px">
                      <el-checkbox :label="s.id" :disabled="teamMembers.length >= currentTeamEvent.team_size && !teamMembers.includes(s.id)">
                        {{ s.name }} ({{ s.gender === 'male' ? '男' : '女' }})
                      </el-checkbox>
                    </div>
                  </el-checkbox-group>
                </el-form-item>
              </el-form>
              <el-button type="primary" :loading="teamSubmitting"
                :disabled="!selectedTeamEvent || teamMembers.length !== (currentTeamEvent?.team_size || 0)"
                @click="submitTeamRegister" style="width:100%">
                {{ teamMembers.length && currentTeamEvent && teamMembers.length < currentTeamEvent.team_size ? `还需选 ${currentTeamEvent.team_size - teamMembers.length} 人` : '提交团体报名' }}
              </el-button>
            </el-col>
            <el-col :span="12">
              <el-card shadow="never" style="background:#f9fafb">
                <template #header><span>已报团体项目 - {{ auth.user?.class_name }}</span></template>
                <div v-if="!teamRegistrations.length" style="color:#999;font-size:14px;text-align:center;padding:20px 0">
                  暂无团体报名
                </div>
                <el-table v-else :data="teamRegistrations" size="small">
                  <el-table-column prop="event_name" label="项目" />
                  <el-table-column label="队员">
                    <template #default="{ row }">
                      {{ row.members?.map(m => m.name || m).join('、') || '-' }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="status" label="状态" width="80" align="center">
                    <template #default="{ row }">
                      <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'" size="small">
                        {{ row.status === 'approved' ? '已通过' : row.status === 'rejected' ? '已拒绝' : '待审核' }}
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

const auth = useAuthStore()
const registerMode = ref('individual')
const meets = ref([])
const events = ref([])
const students = ref([])
const teamRegistrations = ref([])
const selectedMeet = ref('')
const currentMeet = computed(() => meets.value.find(m => m.id === selectedMeet.value))
const selectedEvent = ref('')
const selectedTeamEvent = ref('')
const selectedStudents = ref([])
const teamMembers = ref([])
const submitting = ref(false)
const teamSubmitting = ref(false)

const newStudent = reactive({ name: '', gender: 'male', student_id: '' })

const genderMap = { male:'男', female:'女', mixed:'混合' }
const genderLabel = g => genderMap[g] || g

const individualEvents = computed(() => events.value.filter(e => !['relay', 'team_confrontation'].includes(e.event_type)))
const teamEvents = computed(() => events.value.filter(e => ['relay', 'team_confrontation'].includes(e.event_type)))
const currentTeamEvent = computed(() => events.value.find(e => e.id == selectedTeamEvent.value))

const filteredTeamStudents = computed(() => {
  const ev = currentTeamEvent.value
  if (!ev) return students.value
  if (ev.gender === 'mixed') return students.value
  return students.value.filter(s => s.gender === ev.gender)
})

function onModeChange() {
  selectedStudents.value = []
  teamMembers.value = []
  selectedEvent.value = ''
  selectedTeamEvent.value = ''
  if (registerMode.value === 'team') loadTeamRegistrations()
}

async function loadEvents() {
  if (!selectedMeet.value) return
  const res = await eventApi.list({ sports_meet: selectedMeet.value })
  events.value = res.results || res
}

async function addStudent() {
  if (!newStudent.name) return ElMessage.warning('请输入姓名')
  await studentApi.create({ ...newStudent, class_name: auth.user.class_name })
  ElMessage.success('添加成功')
  newStudent.name = ''; newStudent.student_id = ''
  loadStudents()
}

async function deleteStudent(row) {
  await ElMessageBox.confirm(`确认删除学生「${row.name}」？`, '提示', { type: 'warning' })
  await studentApi.delete(row.id)
  ElMessage.success('已删除')
  loadStudents()
}

async function loadStudents() {
  const res = await studentApi.list({ class_name: auth.user.class_name })
  students.value = res.results || res
}

async function loadTeamRegistrations() {
  const res = await teamRegistrationApi.list({ class_name: auth.user.class_name })
  const data = res.results || res
  // enrich with event name
  data.forEach(tr => {
    if (tr.event) {
      const ev = events.value.find(e => e.id === tr.event)
      tr.event_name = ev ? ev.name : ''
    }
  })
  teamRegistrations.value = data
}

async function submitRegister() {
  submitting.value = true
  try {
    const res = await registrationApi.bulkRegister({
      event_id: selectedEvent.value,
      student_ids: selectedStudents.value
    })
    const created = res.created || []
    const errors = res.errors || []
    if (created.length) ElMessage.success(`成功报名 ${created.length} 人：${created.join('、')}`)
    if (errors.length) ElMessage.warning(`以下报名失败：${errors.join('；')}`)
    selectedStudents.value = []
  } finally {
    submitting.value = false
  }
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
  } finally {
    teamSubmitting.value = false
  }
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
