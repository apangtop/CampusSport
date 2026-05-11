<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <span style="font-size:16px;font-weight:600">为本班学生报名</span>
      </template>
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
              <el-select v-model="selectedEvent" style="width:100%" placeholder="选择项目" clearable>
                <el-option v-for="e in events" :key="e.id"
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
            <div style="margin-bottom:8px;font-size:12px;color:#888">
              班级：<strong>{{ auth.user?.class_name || '未绑定班级' }}</strong>（自动关联）
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
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { meetApi, eventApi, studentApi, registrationApi } from '@/api'

const auth = useAuthStore()
const meets = ref([])
const events = ref([])
const students = ref([])
const selectedMeet = ref('')
const currentMeet = computed(() => meets.value.find(m => m.id === selectedMeet.value))
const selectedEvent = ref('')
const selectedStudents = ref([])
const submitting = ref(false)

const newStudent = reactive({ name: '', gender: 'male', student_id: '' })

const genderMap = { male:'男', female:'女', mixed:'混合' }
const genderLabel = g => genderMap[g] || g

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
