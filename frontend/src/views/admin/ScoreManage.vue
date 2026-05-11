<template>
  <div>
    <el-page-header content="成绩管理" @back="$router.push(`/admin/meets/${meetId}`)" style="margin-bottom:20px" />
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div style="display:flex;gap:12px;align-items:center">
            <el-select v-model="filterEvent" placeholder="选择项目" style="width:200px" @change="loadScores">
              <el-option v-for="e in events" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
            <el-select v-model="filterStage" placeholder="阶段" style="width:120px" @change="loadScores">
              <el-option label="决赛" value="final" />
              <el-option label="初赛" value="preliminary" />
              <el-option label="半决赛" value="semifinal" />
            </el-select>
            <ClassSelector v-model="filterClass" @change="loadScores" :clearable="true" style="margin-left:0" />
          </div>
          <div style="display:flex;gap:8px">
            <el-button v-if="isAdvancementStage" type="warning" @click="confirmAdvance" :disabled="!selectedRegistrations.length">
              确认晋级（{{ selectedRegistrations.length }} 人）
            </el-button>
            <el-button @click="calcRanks" :disabled="!filterEvent">重新计算排名</el-button>
          </div>
        </div>
      </template>
      <el-table :data="scores" v-loading="loading" @selection-change="onSelectionChange">
        <el-table-column v-if="isAdvancementStage" type="selection" width="50" align="center" />
        <el-table-column prop="rank" label="名次" width="70" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.rank <= 3" :type="['', 'warning', '', 'info'][row.rank]" size="small">
              第{{ row.rank }}名
            </el-tag>
            <span v-else-if="row.rank">第{{ row.rank }}名</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="student_name" label="姓名" width="100" />
        <el-table-column prop="class_name" label="班级" width="120" />
        <el-table-column prop="result" label="成绩" width="120" align="center" />
        <el-table-column prop="points" label="积分" width="80" align="center" />
        <el-table-column prop="stage" label="阶段" width="90" align="center">
          <template #default="{ row }">{{ stageLabel(row.stage) }}</template>
        </el-table-column>
        <el-table-column v-if="filterStage === 'preliminary' || filterStage === 'semifinal'" label="晋级" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_advanced" type="success" size="small">已晋级</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { scoreApi, eventApi } from '@/api'

const route = useRoute()
const meetId = route.params.id
const scores = ref([])
const events = ref([])
const loading = ref(false)
const filterEvent = ref('')
const filterStage = ref('final')
const filterClass = ref('')

const selectedRegistrations = ref([])
const isAdvancementStage = computed(() =>
  filterStage.value === 'preliminary' || filterStage.value === 'semifinal'
)

const stageMap = { preliminary:'初赛', semifinal:'半决赛', final:'决赛' }
const stageLabel = s => stageMap[s] || s

function onSelectionChange(rows) {
  selectedRegistrations.value = rows
}

async function confirmAdvance() {
  try {
    const regIds = selectedRegistrations.value.map(r => r.registration)
    await scoreApi.confirmAdvancement({
      event_id: filterEvent.value,
      stage: filterStage.value,
      registration_ids: regIds
    })
    ElMessage.success('晋级名单已确认，选手已分配至下一阶段赛程')
    selectedRegistrations.value = []
    loadScores()
  } catch {}
}

async function loadScores() {
  if (!filterEvent.value) return
  loading.value = true
  const params = { event: filterEvent.value, stage: filterStage.value }
  if (filterClass.value) params.class_name = filterClass.value
  const res = await scoreApi.list(params)
  scores.value = (res.results || res).sort((a, b) => (a.rank || 999) - (b.rank || 999))
  loading.value = false
}

async function calcRanks() {
  await scoreApi.calculateRanks({ event_id: filterEvent.value, stage: filterStage.value })
  ElMessage.success('排名已重新计算')
  loadScores()
}

onMounted(async () => {
  const res = await eventApi.list({ sports_meet: meetId })
  events.value = res.results || res
  if (events.value.length) {
    filterEvent.value = events.value[0].id
    loadScores()
  }
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
