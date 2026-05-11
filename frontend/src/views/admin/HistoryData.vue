<template>
  <div>
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 历届运动会 -->
      <el-tab-pane label="历届运动会" name="meets">
        <el-table :data="historyMeets" v-loading="loadingMeets">
          <el-table-column prop="session" label="届次" width="80" align="center">
            <template #default="{ row }">第{{ row.session }}届</template>
          </el-table-column>
          <el-table-column prop="name" label="名称" min-width="160" />
          <el-table-column prop="school" label="学校" width="140" />
          <el-table-column prop="start_date" label="日期" width="130" />
          <el-table-column prop="event_count" label="项目数" width="80" align="center" />
        </el-table>
      </el-tab-pane>

      <!-- 历届积分榜 -->
      <el-tab-pane label="历届积分榜" name="points">
        <div style="margin-bottom:16px">
          <el-select v-model="filterPointsMeet" placeholder="选择届次" clearable style="width:200px" @change="loadPoints">
            <el-option v-for="m in historyMeets" :key="m.id" :label="`第${m.session}届 ${m.name}`" :value="m.id" />
          </el-select>
        </div>
        <el-table :data="historyPoints" v-loading="loadingPoints">
          <el-table-column prop="session" label="届次" width="80" align="center">
            <template #default="{ row }">第{{ row.session }}届</template>
          </el-table-column>
          <el-table-column prop="rank" label="排名" width="80" align="center">
            <template #default="{ row }">
              <span v-if="row.rank===1">🥇</span>
              <span v-else-if="row.rank===2">🥈</span>
              <span v-else-if="row.rank===3">🥉</span>
              <span v-else>{{ row.rank }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="class_name" label="班级" min-width="120" />
          <el-table-column prop="total_points" label="总积分" width="100" align="center">
            <template #default="{ row }">
              <span style="font-weight:700;color:#1a6db5">{{ row.total_points }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="gold_medals" label="🥇" width="70" align="center" />
          <el-table-column prop="silver_medals" label="🥈" width="70" align="center" />
          <el-table-column prop="bronze_medals" label="🥉" width="70" align="center" />
        </el-table>
      </el-tab-pane>

      <!-- 项目历史最佳 -->
      <el-tab-pane label="项目历史最佳" name="eventBest">
        <div style="display:flex;gap:12px;margin-bottom:16px">
          <el-select v-model="filterEventName" placeholder="选择项目" style="width:220px" @change="loadEventBest">
            <el-option v-for="n in eventNames" :key="n" :label="n" :value="n" />
          </el-select>
        </div>
        <el-table :data="eventBest" v-loading="loadingEventBest">
          <el-table-column prop="session" label="届次" width="80" align="center">
            <template #default="{ row }">第{{ row.session }}届</template>
          </el-table-column>
          <el-table-column prop="meet_name" label="运动会" width="160" />
          <el-table-column prop="student_name" label="冠军" width="100" />
          <el-table-column prop="class_name" label="班级" width="120" />
          <el-table-column prop="result" label="成绩" width="120" align="center">
            <template #default="{ row }">
              <el-tag type="success">{{ row.result }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="start_date" label="日期" width="120" />
        </el-table>
      </el-tab-pane>

      <!-- 学生参赛历史 -->
      <el-tab-pane label="学生参赛历史" name="student">
        <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;align-items:center">
          <el-input v-model="filterStudentName" placeholder="搜索学生姓名" clearable style="width:160px" />
          <ClassSelector v-model="filterStudentClass" :clearable="true" />
          <el-button type="primary" @click="loadStudentHistory">查询</el-button>
        </div>
        <el-table :data="studentHistory" v-loading="loadingStudent">
          <el-table-column prop="session" label="届次" width="80" align="center">
            <template #default="{ row }">第{{ row.session }}届</template>
          </el-table-column>
          <el-table-column prop="student_name" label="学生" width="100" />
          <el-table-column prop="class_name" label="班级" width="120" />
          <el-table-column prop="event_name" label="参赛项目" min-width="130" />
          <el-table-column prop="result" label="成绩" width="120" align="center" />
          <el-table-column prop="rank" label="名次" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.rank" :type="row.rank===1?'warning':row.rank===2?'info':''" size="small">
                第{{ row.rank }}名
              </el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="points" label="积分" width="80" align="center" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { historyApi } from '@/api'
import ClassSelector from '@/components/ClassSelector.vue'

const activeTab = ref('meets')
const historyMeets = ref([])
const historyPoints = ref([])
const eventNames = ref([])
const eventBest = ref([])
const studentHistory = ref([])
const filterPointsMeet = ref('')
const filterEventName = ref('')
const filterStudentName = ref('')
const filterStudentClass = ref('')

const loadingMeets = ref(false)
const loadingPoints = ref(false)
const loadingEventBest = ref(false)
const loadingStudent = ref(false)

async function loadMeets() {
  loadingMeets.value = true
  const res = await historyApi.meets()
  historyMeets.value = Array.isArray(res) ? res : (res.results || [])
  loadingMeets.value = false
}

async function loadPoints() {
  loadingPoints.value = true
  const params = {}
  if (filterPointsMeet.value) params.sports_meet = filterPointsMeet.value
  const res = await historyApi.points(params)
  historyPoints.value = Array.isArray(res) ? res : (res.results || [])
  loadingPoints.value = false
}

async function loadEventNames() {
  const res = await historyApi.eventBest({})
  eventNames.value = Array.isArray(res) ? res : []
}

async function loadEventBest() {
  if (!filterEventName.value) return
  loadingEventBest.value = true
  const res = await historyApi.eventBest({ event_name: filterEventName.value })
  eventBest.value = Array.isArray(res) ? res : (res.results || [])
  loadingEventBest.value = false
}

async function loadStudentHistory() {
  loadingStudent.value = true
  const params = {}
  if (filterStudentName.value) params.name = filterStudentName.value
  if (filterStudentClass.value) params.class_name = filterStudentClass.value
  const res = await historyApi.student(params)
  studentHistory.value = Array.isArray(res) ? res : (res.results || [])
  loadingStudent.value = false
}

onMounted(() => {
  loadMeets()
  loadEventNames()
})
</script>
