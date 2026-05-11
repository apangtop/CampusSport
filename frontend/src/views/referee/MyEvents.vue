<template>
  <div>
    <el-card shadow="never">
      <template #header><span style="font-size:16px;font-weight:600">我的项目详情</span></template>
      <el-table :data="events" v-loading="loading">
        <el-table-column prop="name" label="项目名称" min-width="140" />
        <el-table-column prop="event_type" label="类型" width="100" align="center">
          <template #default="{ row }">{{ typeLabel(row.event_type) }}</template>
        </el-table-column>
        <el-table-column prop="gender" label="性别" width="70" align="center">
          <template #default="{ row }">{{ genderLabel(row.gender) }}</template>
        </el-table-column>
        <el-table-column prop="stage_type" label="赛制" width="130">
          <template #default="{ row }">{{ stageLabel(row.stage_type) }}</template>
        </el-table-column>
        <el-table-column prop="registration_count" label="参赛人数" width="90" align="center" />
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/referee/score-entry?event=${row.id}`)">录入成绩</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { eventApi } from '@/api'

const events = ref([])
const loading = ref(false)

const typeMap = { track:'径赛', field:'田赛', fun_individual:'趣味个人', team_confrontation:'对抗团体', relay:'接力团体' }
const typeLabel = t => typeMap[t] || t
const genderMap = { male:'男', female:'女', mixed:'混合' }
const genderLabel = g => genderMap[g] || g
const stageMap = { single:'直接决赛', two:'两阶段(初赛+决赛)', three:'三阶段' }
const stageLabel = s => stageMap[s] || s

onMounted(async () => {
  loading.value = true
  const res = await eventApi.list()
  events.value = res.results || res
  loading.value = false
})
</script>
