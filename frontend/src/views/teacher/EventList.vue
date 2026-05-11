<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">项目浏览</span>
          <el-select v-model="filterMeet" placeholder="选择运动会" style="width:200px" @change="loadEvents">
            <el-option v-for="m in meets" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </div>
      </template>
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
        <el-table-column prop="max_per_class" label="班级上限" width="90" align="center" />
        <el-table-column prop="referee_name" label="裁判" width="100" />
        <el-table-column prop="registration_count" label="已报名" width="80" align="center" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { meetApi, eventApi } from '@/api'

const meets = ref([])
const events = ref([])
const loading = ref(false)
const filterMeet = ref('')

const typeMap = { track:'径赛', field:'田赛', fun_individual:'趣味个人', team_confrontation:'对抗团体', relay:'接力团体' }
const typeLabel = t => typeMap[t] || t
const genderMap = { male:'男', female:'女', mixed:'混合' }
const genderLabel = g => genderMap[g] || g
const stageMap = { single:'直接决赛', two:'两阶段(初赛+决赛)', three:'三阶段' }
const stageLabel = s => stageMap[s] || s

async function loadEvents() {
  if (!filterMeet.value) return
  loading.value = true
  const res = await eventApi.list({ sports_meet: filterMeet.value })
  events.value = res.results || res
  loading.value = false
}

onMounted(async () => {
  const res = await meetApi.list()
  meets.value = res.results || res
  if (meets.value.length) {
    filterMeet.value = meets.value[0].id
    loadEvents()
  }
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
