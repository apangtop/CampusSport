<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">成绩查看</span>
          <div style="display:flex;gap:8px">
            <el-select v-model="filterMeet" placeholder="选择运动会" style="width:200px" @change="load">
              <el-option v-for="m in meets" :key="m.id" :label="m.name" :value="m.id" />
            </el-select>
            <el-select v-model="filterStage" clearable placeholder="阶段" style="width:100px" @change="load">
              <el-option label="全部" value="" />
              <el-option label="决赛" value="final" />
              <el-option label="初赛" value="preliminary" />
              <el-option label="半决赛" value="semifinal" />
            </el-select>
          </div>
        </div>
      </template>
      <el-table :data="scores" v-loading="loading">
        <el-table-column label="名次" width="70" align="center">
          <template #default="{ row }">
            <span v-if="row.rank === 1">🥇</span>
            <span v-else-if="row.rank === 2">🥈</span>
            <span v-else-if="row.rank === 3">🥉</span>
            <span v-else-if="row.rank">第{{ row.rank }}名</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="student_name" label="学生" width="90" />
        <el-table-column prop="event_name" label="项目" min-width="140" />
        <el-table-column label="阶段" width="80" align="center">
          <template #default="{ row }">{{ stageMap[row.stage] || row.stage }}</template>
        </el-table-column>
        <el-table-column prop="result" label="成绩" width="100" align="center" />
        <el-table-column prop="points" label="积分" width="70" align="center" />
      </el-table>
      <el-empty v-if="!scores.length && !loading" description="暂无成绩" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup>
import { loadAllPages } from '@/utils/registration'
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { meetApi, scoreApi, teamScoreApi } from '@/api'

const auth = useAuthStore()
const meets = ref([])
const scores = ref([])
const loading = ref(false)
const filterMeet = ref('')
const filterStage = ref('')

const stageMap = { preliminary:'初赛', semifinal:'半决赛', final:'决赛' }

let loadVersion = 0
async function load() {
  const version = ++loadVersion
  if (!filterMeet.value) { scores.value = []; loading.value = false; return }
  loading.value = true
  const params = { sports_meet: filterMeet.value, class_name: auth.user?.class_name }
  if (filterStage.value) params.stage = filterStage.value
  try {
    const [res, teams] = await Promise.all([
      loadAllPages(p => scoreApi.list(p), params),
      loadAllPages(p => teamScoreApi.list(p), params)
    ])
    if (version !== loadVersion) return
    scores.value = [...(res.results || res), ...(teams.results || teams).map(s => ({ ...s, student_name: '团体' }))]
      .sort((a, b) => (a.rank || 999) - (b.rank || 999))
  } finally { if (version === loadVersion) loading.value = false }
}

onMounted(async () => {
  const res = await loadAllPages(p => meetApi.list(p))
  meets.value = res.results || res
  if (meets.value.length) { filterMeet.value = meets.value[0].id; load() }
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
</style>
