<template>
  <div>
    <el-page-header content="参赛人员总览" @back="$router.push(`/admin/meets/${meetId}`)" style="margin-bottom:20px" />

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <el-select v-model="filterEvent" placeholder="选择项目" style="width:260px" @change="load">
            <el-option-group v-for="type in groupedEvents" :key="type.label" :label="type.label">
              <el-option v-for="e in type.events" :key="e.id" :label="`${e.name}（${e.registration_count}人已报）`" :value="e.id" />
            </el-option-group>
          </el-select>
          <el-tag v-if="currentEvent" type="info" size="large">
            {{ typeLabel(currentEvent.event_type) }} | {{ genderLabel(currentEvent.gender) }} | {{ stageLabel(currentEvent.stage_type) }}
          </el-tag>
        </div>
      </template>

      <div v-if="currentEvent">
        <!-- 团体项目 -->
        <template v-if="isTeamEvent">
          <el-table :data="teamParticipants" v-loading="loading" size="small">
            <el-table-column prop="lane" :label="needsLanes(currentEvent?.event_type) ? '道次' : '序号'" width="60" align="center">
              <template #default="{ row }">{{ row.lane || '-' }}</template>
            </el-table-column>
            <el-table-column prop="class_name" label="班级" width="150" />
            <el-table-column label="队员" min-width="300">
              <template #default="{ row }">
                <el-tag v-for="m in row.members" :key="m.id" size="small" style="margin:2px"
                  :type="row.class_name === auth.user?.class_name ? 'warning' : ''">
                  {{ m.name }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'approved' ? 'success' : 'warning'" size="small">
                  {{ row.status === 'approved' ? '已审核' : '待审核' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <!-- 个人项目 -->
        <template v-else>
          <div v-if="!groupedParticipants.length" v-loading="loading" style="text-align:center;color:#999;padding:40px">
            暂无参赛人员
          </div>
          <div v-for="grp in groupedParticipants" :key="grp.key" style="margin-bottom:24px">
            <h4 style="margin:0 0 8px;color:#303133">
              {{ grp.stageLabel }}
              <el-tag size="small" type="warning" style="margin-left:8px">第{{ grp.group }}组</el-tag>
              <span style="font-size:13px;color:#999;margin-left:8px">
                {{ grp.venue || '场地待定' }} {{ grp.time || '' }}
              </span>
            </h4>
            <el-table :data="grp.participants" size="small">
              <el-table-column prop="lane" :label="needsLanes(currentEvent?.event_type) ? '道次' : '序号'" width="60" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.lane" size="small" type="warning">{{ row.lane }}</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="student.name" label="姓名" width="100" />
              <el-table-column prop="student.class_name" label="班级" width="130" />
              <el-table-column prop="student.gender" label="性别" width="60" align="center">
                <template #default="{ row }">{{ row.student.gender === 'male' ? '男' : '女' }}</template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="80" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'approved' ? 'success' : 'warning'" size="small">
                    {{ row.status === 'approved' ? '已审核' : '待审' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>
      </div>

      <el-empty v-else description="请选择一个项目查看参赛人员" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { eventApi, teamRegistrationApi } from '@/api'
import { shortDatetime, needsLanes } from '@/utils/format'

const route = useRoute()
const auth = useAuthStore()
const meetId = route.params.id
const events = ref([])
const participants = ref([])
const teamParticipants = ref([])
const loading = ref(false)
const filterEvent = ref('')

const currentEvent = computed(() => events.value.find(e => e.id == filterEvent.value))
const isTeamEvent = computed(() =>
  currentEvent.value && ['relay', 'team_confrontation'].includes(currentEvent.value.event_type)
)

const typeMap = { track:'径赛', field:'田赛', fun_individual:'趣味', relay:'接力', team_confrontation:'对抗' }
const typeLabel = t => typeMap[t] || t
const genderMap = { male:'男', female:'女', mixed:'混合' }
const genderLabel = g => genderMap[g] || g
const stageMap = { single:'直接决赛', two:'初赛+决赛', three:'初赛+半决赛+决赛' }
const stageLabel = s => stageMap[s] || s
const stageNameMap = { preliminary:'初赛', final:'决赛' }

const groupedEvents = computed(() => {
  const groups = {}
  for (const e of events.value) {
    const t = e.event_type
    if (!groups[t]) groups[t] = { label: typeLabel(t), events: [] }
    groups[t].events.push(e)
  }
  return Object.values(groups)
})

const groupedParticipants = computed(() => {
  // 按 schedule(stage + group) 分组
  const groups = {}
  for (const p of participants.value) {
    const si = p.schedule_info
    const key = si ? `${si.stage}-${si.group_number}` : 'unassigned'
    if (!groups[key]) {
      groups[key] = {
        key,
        stage: si?.stage || 'unassigned',
        stageLabel: si ? stageNameMap[si.stage] || si.stage : '未分组',
        group: si?.group_number || '-',
        time: shortDatetime(si?.scheduled_time),
        venue: si?.venue || '',
        participants: []
      }
    }
    groups[key].participants.push(p)
  }
  const order = ['preliminary', 'final', 'unassigned']
  return Object.values(groups).sort((a, b) => {
    const ai = order.indexOf(a.stage), bi = order.indexOf(b.stage)
    if (ai !== bi) return ai - bi
    return String(a.group).localeCompare(String(b.group), undefined, { numeric: true })
  })
})

async function load() {
  if (!filterEvent.value) return
  loading.value = true
  if (isTeamEvent.value) {
    const res = await teamRegistrationApi.list({ event: filterEvent.value, page_size: 200 })
    teamParticipants.value = res.results || res
    participants.value = []
  } else {
    const res = await eventApi.participants(filterEvent.value)
    participants.value = (res.results || res).sort((a, b) =>
      (a.lane || 999) - (b.lane || 999)
    )
    teamParticipants.value = []
  }
  loading.value = false
}

onMounted(async () => {
  const res = await eventApi.list({ sports_meet: meetId, page_size: 200 })
  events.value = res.results || res
  if (events.value.length) {
    filterEvent.value = events.value[0].id
    load()
  }
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
</style>
