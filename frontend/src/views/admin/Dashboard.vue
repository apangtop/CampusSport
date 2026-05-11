<template>
  <div>
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="s in stats" :key="s.label">
        <el-card class="stat-card" shadow="never">
          <div class="stat-inner">
            <div class="stat-icon" :style="{ background: s.color }">
              <el-icon :size="28"><component :is="s.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ s.value }}</div>
              <div class="stat-label">{{ s.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>运动会列表</span>
              <el-button type="primary" size="small" @click="$router.push('/admin/meets')">
                查看全部
              </el-button>
            </div>
          </template>
          <el-table :data="meets" size="small">
            <el-table-column prop="name" label="运动会名称" />
            <el-table-column prop="session" label="届次" width="70" align="center">
              <template #default="{ row }">第{{ row.session }}届</template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="event_count" label="项目数" width="80" align="center" />
            <el-table-column label="操作" width="120" align="center">
              <template #default="{ row }">
                <el-button link type="primary" @click="$router.push(`/admin/meets/${row.id}`)">
                  进入
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <template #header><span>快捷操作</span></template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/admin/meets')" block>
              <el-icon><Plus /></el-icon> 新建运动会
            </el-button>
            <el-button @click="$router.push('/admin/accounts')" block>
              <el-icon><UserFilled /></el-icon> 管理账号
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { meetApi } from '@/api'

const meets = ref([])
const stats = ref([
  { label: '运动会总数', value: 0, icon: 'Trophy', color: '#1a6db5' },
  { label: '进行中', value: 0, icon: 'VideoPlay', color: '#67c23a' },
  { label: '报名中', value: 0, icon: 'EditPen', color: '#e6a23c' },
  { label: '已结束', value: 0, icon: 'CircleCheck', color: '#909399' },
])

const statusMap = {
  preparing: { label: '筹备中', type: 'info' },
  registration: { label: '报名中', type: 'warning' },
  ongoing: { label: '进行中', type: 'success' },
  finished: { label: '已结束', type: '' }
}
const statusLabel = s => statusMap[s]?.label || s
const statusType = s => statusMap[s]?.type || ''

onMounted(async () => {
  const res = await meetApi.list()
  meets.value = res.results || res
  stats.value[0].value = meets.value.length
  stats.value[1].value = meets.value.filter(m => m.status === 'ongoing').length
  stats.value[2].value = meets.value.filter(m => m.status === 'registration').length
  stats.value[3].value = meets.value.filter(m => m.status === 'finished').length
})
</script>

<style scoped>
.stat-row .stat-card { border-radius: 10px; }
.stat-inner { display: flex; align-items: center; gap: 16px; }
.stat-icon {
  width: 56px; height: 56px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; color: #fff;
}
.stat-value { font-size: 28px; font-weight: 700; line-height: 1; }
.stat-label { font-size: 13px; color: #888; margin-top: 4px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.quick-actions { display: flex; flex-direction: column; gap: 12px; }
</style>
