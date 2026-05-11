<template>
  <div>
    <el-page-header content="班级积分榜" @back="$router.push(`/admin/meets/${meetId}`)" style="margin-bottom:20px" />
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div style="display:flex;gap:12px;align-items:center">
            <span>班级积分排名</span>
            <el-select v-model="filterGrade" placeholder="选择年级" style="width:180px" @change="load" clearable>
              <el-option label="全校总榜" value="" />
              <el-option label="2028级（初一）" value="2028级" />
              <el-option label="2027级（初二）" value="2027级" />
              <el-option label="2026级（初三）" value="2026级" />
            </el-select>
          </div>
          <el-button @click="recalculate">重新计算积分</el-button>
        </div>
      </template>
      <el-table :data="points" v-loading="loading" :row-class-name="rowClass">
        <el-table-column prop="rank" label="排名" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.rank === 1" style="font-size:22px">🥇</span>
            <span v-else-if="row.rank === 2" style="font-size:22px">🥈</span>
            <span v-else-if="row.rank === 3" style="font-size:22px">🥉</span>
            <el-tag v-else type="info" size="small">第{{ row.rank }}名</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" min-width="120" />
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
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { pointsApi } from '@/api'

const route = useRoute()
const meetId = route.params.id
const points = ref([])
const loading = ref(false)
const filterGrade = ref('')

const rowClass = ({ row }) => {
  if (row.rank === 1) return 'row-gold'
  if (row.rank === 2) return 'row-silver'
  if (row.rank === 3) return 'row-bronze'
  return ''
}

async function load() {
  loading.value = true
  const params = { sports_meet: meetId }
  if (filterGrade.value !== '') params.grade = filterGrade.value
  const res = await pointsApi.list(params)
  points.value = res.results || res
  loading.value = false
}

async function recalculate() {
  await pointsApi.recalculate({ sports_meet_id: meetId })
  ElMessage.success('积分已重新计算')
  load()
}

onMounted(load)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
<style>
.row-gold td { background: #fffbe6 !important; }
.row-silver td { background: #f5f5f5 !important; }
.row-bronze td { background: #fff7e6 !important; }
</style>
