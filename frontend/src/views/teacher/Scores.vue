<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">成绩查看</span>
          <el-select v-model="filterMeet" placeholder="选择运动会" style="width:200px" @change="load">
            <el-option v-for="m in meets" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </div>
      </template>
      <el-tabs v-model="tab">
        <el-tab-pane label="本班成绩" name="my">
          <el-table :data="myScores" v-loading="loading">
            <el-table-column prop="rank" label="名次" width="80" align="center">
              <template #default="{ row }">{{ row.rank ? `第${row.rank}名` : '-' }}</template>
            </el-table-column>
            <el-table-column prop="student_name" label="学生" width="100" />
            <el-table-column prop="event_name" label="项目" min-width="130" />
            <el-table-column prop="result" label="成绩" width="120" align="center" />
            <el-table-column prop="points" label="积分" width="80" align="center" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="全部成绩" name="all">
          <el-table :data="allScores" v-loading="loading">
            <el-table-column prop="rank" label="名次" width="80" align="center">
              <template #default="{ row }">{{ row.rank ? `第${row.rank}名` : '-' }}</template>
            </el-table-column>
            <el-table-column prop="student_name" label="学生" width="100" />
            <el-table-column prop="class_name" label="班级" width="110" />
            <el-table-column prop="event_name" label="项目" min-width="130" />
            <el-table-column prop="result" label="成绩" width="120" align="center" />
            <el-table-column prop="points" label="积分" width="80" align="center" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { meetApi, scoreApi } from '@/api'

const auth = useAuthStore()
const meets = ref([])
const myScores = ref([])
const allScores = ref([])
const loading = ref(false)
const filterMeet = ref('')
const tab = ref('my')

async function load() {
  if (!filterMeet.value) return
  loading.value = true
  const [myRes, allRes] = await Promise.all([
    scoreApi.list({ sports_meet: filterMeet.value, class_name: auth.user?.class_name }),
    scoreApi.list({ sports_meet: filterMeet.value })
  ])
  myScores.value = myRes.results || myRes
  allScores.value = allRes.results || allRes
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
