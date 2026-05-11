<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">班级积分榜</span>
          <div style="display:flex;gap:8px">
            <el-select v-model="filterMeet" placeholder="选择运动会" style="width:200px" @change="load">
              <el-option v-for="m in meets" :key="m.id" :label="m.name" :value="m.id" />
            </el-select>
            <el-select v-model="filterGrade" style="width:160px" @change="load">
              <el-option label="本年级排名" :value="teacherGrade" />
              <el-option label="全校总榜" value="" />
            </el-select>
          </div>
        </div>
      </template>
      <el-table :data="points" v-loading="loading" :row-class-name="rowClass">
        <el-table-column prop="rank" label="排名" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.rank === 1" style="font-size:20px">🥇</span>
            <span v-else-if="row.rank === 2" style="font-size:20px">🥈</span>
            <span v-else-if="row.rank === 3" style="font-size:20px">🥉</span>
            <span v-else>{{ row.rank }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" min-width="120">
          <template #default="{ row }">
            <span :style="row.class_name === auth.user?.class_name ? 'font-weight:700;color:#1a6db5' : ''">
              {{ row.class_name }}
              <el-tag v-if="row.class_name === auth.user?.class_name" size="small" type="primary" style="margin-left:6px">我班</el-tag>
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="total_points" label="总积分" width="110" align="center">
          <template #default="{ row }">
            <span style="font-size:18px;font-weight:700;color:#1a6db5">{{ row.total_points }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="gold_medals" label="🥇" width="70" align="center" />
        <el-table-column prop="silver_medals" label="🥈" width="70" align="center" />
        <el-table-column prop="bronze_medals" label="🥉" width="70" align="center" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { meetApi, pointsApi } from '@/api'
import { extractGrade } from '@/utils/format'

const auth = useAuthStore()
const teacherGrade = extractGrade(auth.user?.class_name)
const meets = ref([])
const points = ref([])
const loading = ref(false)
const filterMeet = ref('')
const filterGrade = ref(teacherGrade)

const rowClass = ({ row }) => {
  if (row.class_name === auth.user?.class_name) return 'row-my-class'
  return ''
}

async function load() {
  if (!filterMeet.value) return
  loading.value = true
  const params = { sports_meet: filterMeet.value }
  if (filterGrade.value) params.grade = filterGrade.value
  const res = await pointsApi.list(params)
  points.value = res.results || res
  loading.value = false
}

onMounted(async () => {
  const res = await meetApi.list()
  meets.value = res.results || res
  if (meets.value.length) { filterMeet.value = meets.value[0].id; load() }
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
<style>
.row-my-class td { background: #ecf5ff !important; }
</style>
