<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">班级积分榜</span>
          <el-select v-model="filterMeet" placeholder="选择运动会" style="width:200px" @change="load">
            <el-option v-for="m in meets" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </div>
      </template>
      <el-table :data="points" v-loading="loading">
        <el-table-column prop="rank" label="排名" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.rank === 1">🥇</span>
            <span v-else-if="row.rank === 2">🥈</span>
            <span v-else-if="row.rank === 3">🥉</span>
            <span v-else>{{ row.rank }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" min-width="130" />
        <el-table-column prop="total_points" label="总积分" width="110" align="center">
          <template #default="{ row }">
            <span style="font-size:18px;font-weight:700;color:#1a6db5">{{ row.total_points }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="gold_medals" label="🥇 金牌" width="90" align="center" />
        <el-table-column prop="silver_medals" label="🥈 银牌" width="90" align="center" />
        <el-table-column prop="bronze_medals" label="🥉 铜牌" width="90" align="center" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { meetApi, pointsApi } from '@/api'

const meets = ref([])
const points = ref([])
const loading = ref(false)
const filterMeet = ref('')

async function load() {
  if (!filterMeet.value) return
  loading.value = true
  const res = await pointsApi.list({ sports_meet: filterMeet.value, page_size: 200 })
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
