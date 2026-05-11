<template>
  <div>
    <el-alert v-if="auth.user?.class_name" type="info" :closable="false" style="margin-bottom:20px">
      当前班级：<strong>{{ auth.user.class_name }}</strong>，您只能为本班学生报名
    </el-alert>
    <el-row :gutter="20">
      <el-col :span="8" v-for="s in stats" :key="s.label">
        <el-card class="stat-card" shadow="never">
          <div class="stat-inner">
            <div class="stat-icon" :style="{ background: s.color }">
              <el-icon :size="26"><component :is="s.icon" /></el-icon>
            </div>
            <div>
              <div class="stat-value">{{ s.value }}</div>
              <div class="stat-label">{{ s.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-card shadow="never" style="margin-top:20px">
      <template #header><span>本班报名情况</span></template>
      <el-table :data="myRegs" v-loading="loading" size="small">
        <el-table-column prop="student_name" label="学生" width="90" />
        <el-table-column prop="event_name" label="项目" min-width="130" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="报名时间" width="160" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { registrationApi } from '@/api'

const auth = useAuthStore()
const myRegs = ref([])
const loading = ref(false)
const stats = ref([
  { label: '已报名项目', value: 0, icon: 'EditPen', color: '#1a6db5' },
  { label: '待审核', value: 0, icon: 'Clock', color: '#e6a23c' },
  { label: '已审核', value: 0, icon: 'CircleCheck', color: '#67c23a' },
])

const statusMap = { submitted:'已提交', approved:'已审核', rejected:'已拒绝', cancelled:'已取消' }
const statusTypeMap = { submitted:'warning', approved:'success', rejected:'danger', cancelled:'info' }
const statusLabel = s => statusMap[s] || s
const statusType = s => statusTypeMap[s] || ''

onMounted(async () => {
  loading.value = true
  const res = await registrationApi.list({ class_name: auth.user?.class_name })
  myRegs.value = res.results || res
  stats.value[0].value = myRegs.value.length
  stats.value[1].value = myRegs.value.filter(r => r.status === 'submitted').length
  stats.value[2].value = myRegs.value.filter(r => r.status === 'approved').length
  loading.value = false
})
</script>

<style scoped>
.stat-card { border-radius: 10px; }
.stat-inner { display: flex; align-items: center; gap: 16px; }
.stat-icon { width: 52px; height: 52px; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #fff; }
.stat-value { font-size: 26px; font-weight: 700; }
.stat-label { font-size: 13px; color: #888; margin-top: 2px; }
</style>
