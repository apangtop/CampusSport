<template>
  <div>
    <el-page-header content="报名审核" @back="$router.push(`/admin/meets/${meetId}`)" style="margin-bottom:20px" />
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
            <el-select v-model="filterEvent" placeholder="筛选项目" clearable style="width:200px" @change="load">
              <el-option v-for="e in events" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
            <ClassSelector v-model="filterClass" @change="load" :clearable="true" />
            <el-select v-model="filterStatus" placeholder="筛选状态" clearable style="width:120px" @change="load">
              <el-option label="已提交" value="submitted" />
              <el-option label="已审核" value="approved" />
              <el-option label="已拒绝" value="rejected" />
            </el-select>
          </div>
          <div style="display:flex;gap:8px">
            <el-button type="success" @click="approveAll">一键审核全部</el-button>
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
        <el-table-column prop="created_at" label="报名时间" width="160" />
        <el-table-column label="操作" width="160" align="center">
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
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { registrationApi, eventApi } from '@/api'
import ClassSelector from '@/components/ClassSelector.vue'

const route = useRoute()
const meetId = route.params.id
const registrations = ref([])
const events = ref([])
const selection = ref([])
const loading = ref(false)
const filterEvent = ref('')
const filterStatus = ref('')
const filterClass = ref('')

const statusMap = { submitted:'已提交', approved:'已审核', rejected:'已拒绝', cancelled:'已取消' }
const statusTypeMap = { submitted:'warning', approved:'success', rejected:'danger', cancelled:'info' }
const statusLabel = s => statusMap[s] || s
const statusType = s => statusTypeMap[s] || ''

async function load() {
  loading.value = true
    const params = { sports_meet: meetId }
    if (filterEvent.value) params.event = filterEvent.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterClass.value) params.class_name = filterClass.value
  const res = await registrationApi.list(params)
  registrations.value = res.results || res
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

async function deleteReg(row) {
  await ElMessageBox.confirm('确认删除此报名？', '提示', { type: 'warning' })
  await registrationApi.delete(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(async () => {
  const res = await eventApi.list({ sports_meet: meetId })
  events.value = res.results || res
  load()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
