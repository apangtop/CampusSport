<template>
  <div>
    <el-card shadow="never">
      <template #header><span style="font-size:16px;font-weight:600">我负责的项目</span></template>
      <el-empty v-if="!loading && events.length === 0" description="暂无分配项目" />
      <el-row :gutter="16">
        <el-col :span="8" v-for="event in events" :key="event.id" style="margin-bottom:16px">
          <el-card shadow="hover" class="event-card">
            <div class="event-type-tag">
              <el-tag :type="typeColor(event.event_type)" size="small">{{ typeLabel(event.event_type) }}</el-tag>
              <el-tag size="small" style="margin-left:4px">{{ genderLabel(event.gender) }}</el-tag>
            </div>
            <h3 class="event-name">{{ event.name }}</h3>
            <div class="event-meta">
              <span>参赛人数：{{ event.registration_count }}</span>
              <span>成绩单位：{{ unitLabel(event.result_unit) }}</span>
            </div>
            <el-button type="primary" size="small" @click="$router.push(`/referee/score-entry?event=${event.id}`)" style="width:100%;margin-top:12px">
              进入录入成绩
            </el-button>
          </el-card>
        </el-col>
      </el-row>
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
const typeColorMap = { track:'', field:'success', fun_individual:'warning', team_confrontation:'danger', relay:'info' }
const typeColor = t => typeColorMap[t] || ''
const genderMap = { male:'男', female:'女', mixed:'混合' }
const genderLabel = g => genderMap[g] || g
const unitMap = { second:'秒', meter:'米', count:'次', rank:'名次' }
const unitLabel = u => unitMap[u] || u

onMounted(async () => {
  loading.value = true
  const res = await eventApi.list()
  events.value = res.results || res
  loading.value = false
})
</script>

<style scoped>
.event-card { border-radius: 10px; }
.event-name { font-size: 17px; font-weight: 700; margin: 10px 0 6px; }
.event-meta { display: flex; gap: 16px; font-size: 13px; color: #888; }
</style>
