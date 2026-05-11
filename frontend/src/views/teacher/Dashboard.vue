<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :xs="12" :sm="6" v-for="card in statCards" :key="card.label">
        <el-card shadow="hover" :body-style="{ padding: '16px' }">
          <div class="stat-inner">
            <span class="stat-num" :style="{ color: card.color }">{{ card.value }}</span>
            <span class="stat-label">{{ card.label }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 当前赛事 + 快捷入口 -->
      <el-col :xs="24" :md="12" style="margin-bottom:16px">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>赛事信息</span>
              <el-select v-model="selectedMeet" style="width:200px" @change="loadAll">
                <el-option v-for="m in activeMeets" :key="m.id" :label="m.name" :value="m.id" />
              </el-select>
            </div>
          </template>
          <el-descriptions v-if="currentMeet" :column="1" border size="small">
            <el-descriptions-item label="状态">
              <el-tag :type="currentMeet.status === 'registration' ? 'warning' : 'success'" size="small">
                {{ statusLabel(currentMeet.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="日期">{{ currentMeet.start_date }} ~ {{ currentMeet.end_date }}</el-descriptions-item>
            <el-descriptions-item label="报名截止">
              <span v-if="currentMeet.registration_deadline" :style="deadlineUrgent ? 'color:#f56c6c;font-weight:600' : ''">
                {{ shortDatetime(currentMeet.registration_deadline) }}
                <el-tag v-if="deadlineUrgent" size="small" type="danger" style="margin-left:6px">即将截止</el-tag>
              </span>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="每人限报">{{ currentMeet.max_events_per_person }} 项</el-descriptions-item>
          </el-descriptions>
          <div v-if="currentMeet" style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
            <el-button type="primary" @click="$router.push('/teacher/events')">浏览项目</el-button>
            <el-button v-if="currentMeet.status === 'registration'" type="success" @click="$router.push('/teacher/register')">去报名</el-button>
            <el-button @click="$router.push('/teacher/my-registrations')">查看报名</el-button>
            <el-button @click="$router.push('/teacher/scores')">查看成绩</el-button>
            <el-button @click="$router.push('/teacher/points')">积分榜</el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 最近报名 -->
      <el-col :xs="24" :md="12" style="margin-bottom:16px">
        <el-card shadow="never">
          <template #header><span>最近报名</span></template>
          <el-table :data="recentRegs" size="small" v-loading="loading">
            <el-table-column prop="student_name" label="学生" width="80" />
            <el-table-column prop="event_name" label="项目" min-width="120" />
            <el-table-column prop="status" label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusMap[row.status] || row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="110">
              <template #default="{ row }">{{ shortDatetime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!recentRegs.length && !loading" description="暂无报名记录" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { meetApi, registrationApi } from '@/api'
import { shortDatetime } from '@/utils/format'

const auth = useAuthStore()
const activeMeets = ref([])
const selectedMeet = ref('')
const allRegs = ref([])
const loading = ref(false)

const statusMap = { submitted:'已提交', approved:'已审核', rejected:'已拒绝', cancelled:'已取消' }
const statusLabel = s => ({ preparing:'筹备中', registration:'报名中', ongoing:'进行中', finished:'已结束' })[s] || s
const statusType = s => ({ submitted:'warning', approved:'success', rejected:'danger', cancelled:'info' })[s] || ''

const currentMeet = computed(() => activeMeets.value.find(m => m.id === selectedMeet.value))
const deadlineUrgent = computed(() => {
  if (!currentMeet.value?.registration_deadline) return false
  return new Date(currentMeet.value.registration_deadline).getTime() - Date.now() < 24 * 3600 * 1000
})

const recentRegs = computed(() => allRegs.value.slice(0, 10))

const statCards = computed(() => {
  return [
    { label: '报名总数', value: allRegs.value.filter(r => r.status !== 'cancelled').length, color: '#1a6db5' },
    { label: '已审核', value: allRegs.value.filter(r => r.status === 'approved').length, color: '#67c23a' },
    { label: '待审核', value: allRegs.value.filter(r => r.status === 'submitted').length, color: '#e6a23c' },
    { label: '班级', value: auth.user?.class_name || '-', color: '#909399' },
  ]
})

async function loadAll() {
  loading.value = true
  const params = { class_name: auth.user?.class_name }
  if (selectedMeet.value) params.sports_meet = selectedMeet.value
  const res = await registrationApi.list(params)
  allRegs.value = res.results || res
  loading.value = false
}

onMounted(async () => {
  const res = await meetApi.list()
  const meets = res.results || res
  activeMeets.value = meets.filter(m => m.status !== 'finished')
  if (activeMeets.value.length) {
    // 优先选进行中的
    const ongoing = activeMeets.value.find(m => m.status === 'ongoing')
    const reg = activeMeets.value.find(m => m.status === 'registration')
    selectedMeet.value = (ongoing || reg || activeMeets.value[0]).id
    loadAll()
  }
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.stat-inner { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.stat-num { font-size: 28px; font-weight: 700; }
.stat-label { font-size: 13px; color: #909399; }
</style>
