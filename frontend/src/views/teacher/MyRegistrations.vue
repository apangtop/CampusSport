<template>
  <div>
    <el-card shadow="never">
      <template #header><span style="font-size:16px;font-weight:600">本班报名情况</span></template>
      <el-table :data="regs" v-loading="loading">
        <el-table-column prop="student_name" label="学生姓名" width="100" />
        <el-table-column prop="event_name" label="报名项目" min-width="140" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lane" label="道次" width="70" align="center">
          <template #default="{ row }">{{ row.lane || '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="报名时间" width="160" />
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-button v-if="row.status === 'submitted'" link type="danger" @click="cancel(row)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { registrationApi } from '@/api'

const auth = useAuthStore()
const regs = ref([])
const loading = ref(false)

const statusMap = { submitted:'已提交', approved:'已审核', rejected:'已拒绝', cancelled:'已取消' }
const statusTypeMap = { submitted:'warning', approved:'success', rejected:'danger', cancelled:'info' }
const statusLabel = s => statusMap[s] || s
const statusType = s => statusTypeMap[s] || ''

async function load() {
  loading.value = true
  const res = await registrationApi.list({ class_name: auth.user?.class_name })
  regs.value = res.results || res
  loading.value = false
}

async function cancel(row) {
  await ElMessageBox.confirm('确认取消此报名？', '提示', { type: 'warning' })
  await registrationApi.update(row.id, { status: 'cancelled' })
  ElMessage.success('已取消')
  load()
}

onMounted(load)
</script>
