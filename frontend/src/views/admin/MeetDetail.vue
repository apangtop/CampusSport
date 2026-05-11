<template>
  <div>
    <el-page-header :content="meet?.name || '运动会详情'" @back="$router.push('/admin/meets')" style="margin-bottom:20px" />

    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="4" v-for="item in navItems" :key="item.path">
        <el-card class="nav-card" shadow="hover" @click="$router.push(item.path)">
          <div class="nav-inner">
            <el-icon :size="32" :color="item.color"><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="10">
        <el-card shadow="never">
          <template #header><span>基本信息</span></template>
          <el-descriptions :column="1" border size="small" v-if="meet">
            <el-descriptions-item label="名称">{{ meet.name }}</el-descriptions-item>
            <el-descriptions-item label="届次">第{{ meet.session }}届</el-descriptions-item>
            <el-descriptions-item label="学校">{{ meet.school || '-' }}</el-descriptions-item>
            <el-descriptions-item label="日期">{{ meet.start_date }} ~ {{ meet.end_date }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusType(meet.status)" size="small">{{ statusLabel(meet.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="报名截止">{{ meet.registration_deadline || '-' }}</el-descriptions-item>
            <el-descriptions-item label="每人项目上限">{{ meet.max_events_per_person }} 个</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card shadow="never">
          <template #header><span>项目列表</span></template>
          <el-table :data="events" size="small" v-loading="loading">
            <el-table-column prop="name" label="项目名称" />
            <el-table-column prop="event_type" label="类型" width="90" align="center">
              <template #default="{ row }">{{ typeLabel(row.event_type) }}</template>
            </el-table-column>
            <el-table-column prop="gender" label="性别" width="70" align="center">
              <template #default="{ row }">{{ genderLabel(row.gender) }}</template>
            </el-table-column>
            <el-table-column prop="registration_count" label="已报名" width="70" align="center" />
            <el-table-column prop="referee_name" label="裁判" width="90" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { meetApi, eventApi } from '@/api'

const route = useRoute()
const meetId = route.params.id
const meet = ref(null)
const events = ref([])
const loading = ref(false)

const navItems = computed(() => [
  { label: '项目管理', icon: 'List', color: '#1a6db5', path: `/admin/meets/${meetId}/events` },
  { label: '报名审核', icon: 'EditPen', color: '#67c23a', path: `/admin/meets/${meetId}/registration` },
  { label: '赛程安排', icon: 'Calendar', color: '#e6a23c', path: `/admin/meets/${meetId}/schedule` },
  { label: '成绩管理', icon: 'DataLine', color: '#f56c6c', path: `/admin/meets/${meetId}/scores` },
  { label: '积分榜', icon: 'Trophy', color: '#9254de', path: `/admin/meets/${meetId}/points` },
  { label: '导出报告', icon: 'Download', color: '#13c2c2', path: `/admin/meets/${meetId}/report` },
])

const statusMap = { preparing:'筹备中', registration:'报名中', ongoing:'进行中', finished:'已结束' }
const statusTypeMap = { preparing:'info', registration:'warning', ongoing:'success', finished:'' }
const statusLabel = s => statusMap[s] || s
const statusType = s => statusTypeMap[s] || ''
const typeMap = { track:'径赛', field:'田赛', fun_individual:'趣味个人', team_confrontation:'对抗团体', relay:'接力团体' }
const typeLabel = t => typeMap[t] || t
const genderMap = { male:'男', female:'女', mixed:'混合' }
const genderLabel = g => genderMap[g] || g

onMounted(async () => {
  loading.value = true
  const [m, e] = await Promise.all([meetApi.get(meetId), eventApi.list({ sports_meet: meetId })])
  meet.value = m
  events.value = e.results || e
  loading.value = false
})
</script>

<style scoped>
.nav-card { cursor: pointer; transition: transform .15s; }
.nav-card:hover { transform: translateY(-3px); }
.nav-inner { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 8px 0; }
.nav-inner span { font-size: 13px; color: #333; }
</style>
