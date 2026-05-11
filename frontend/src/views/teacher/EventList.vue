<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">竞赛项目</span>
          <el-select v-model="filterMeet" placeholder="选择运动会" style="width:200px" @change="loadEvents">
            <el-option v-for="m in meets" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </div>
      </template>

      <el-alert v-if="currentMeet" type="info" :closable="false" style="margin-bottom:16px">
        <template #title>
          {{ currentMeet.name }} · {{ statusLabel(currentMeet.status) }}
          <span v-if="currentMeet.registration_deadline"> · 报名截止：{{ shortDatetime(currentMeet.registration_deadline) }}</span>
          · 我的班级：<strong>{{ auth.user?.class_name }}</strong>
        </template>
      </el-alert>

      <div v-for="group in groupedEvents" :key="group.label" style="margin-bottom:16px">
        <h4 style="margin:0 0 8px;color:#606266">{{ group.label }}</h4>
        <div style="display:flex;flex-wrap:wrap;gap:8px">
          <el-card
            v-for="ev in group.events" :key="ev.id"
            class="event-card" shadow="hover"
            :style="{ borderTop: `3px solid ${eventColor(ev.event_type)}` }"
          >
            <div class="event-name">{{ ev.name }}</div>
            <div class="event-meta">
              {{ genderLabel(ev.gender) }}
              <el-tag v-if="ev.grade" size="small" :type="ev.grade === teacherGrade ? 'success' : 'info'" style="margin-left:4px">
                {{ ev.grade }}
              </el-tag>
            </div>
            <div class="event-info">👤 裁判：{{ ev.referee_name || '待定' }}</div>
            <div class="event-info">📋 本班已报 {{ classRegCounts[ev.id] || 0 }} / {{ ev.max_per_class }} 人</div>
            <div class="event-info">🏃 {{ stageLabel(ev.stage_type) }} · {{ unitLabel(ev.result_unit) }}</div>
          </el-card>
        </div>
      </div>

      <el-empty v-if="!events.length && !loading" description="暂无比赛项目" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { meetApi, eventApi, registrationApi, teamRegistrationApi } from '@/api'
import { extractGrade, shortDatetime } from '@/utils/format'

const auth = useAuthStore()
const teacherGrade = extractGrade(auth.user?.class_name)
const meets = ref([])
const events = ref([])
const classRegCounts = ref({}) // event_id → 本班已报人数
const loading = ref(false)
const filterMeet = ref('')

const currentMeet = computed(() => meets.value.find(m => m.id === filterMeet.value))

const filteredEvents = computed(() => events.value.filter(e =>
  !e.grade || e.grade === teacherGrade
))

const groupedEvents = computed(() => {
  const groups = {}
  for (const e of filteredEvents.value) {
    const t = e.event_type
    if (!groups[t]) groups[t] = { label: typeLabel(t), events: [] }
    groups[t].events.push(e)
  }
  return Object.values(groups)
})

const typeMap = { track:'径赛', field:'田赛', fun_individual:'趣味', relay:'接力团体', team_confrontation:'对抗' }
const typeLabel = t => typeMap[t] || t
const genderMap = { male:'男', female:'女', mixed:'混合' }
const genderLabel = g => genderMap[g] || g
const stageMap = { single:'直接决赛', two:'初赛+决赛', three:'三阶段' }
const stageLabel = s => stageMap[s] || s
const unitMap = { second:'秒', meter:'米', count:'次', rank:'名次' }
const unitLabel = u => unitMap[u] || u
const eventColors = { track:'#409eff', field:'#67c23a', fun_individual:'#e6a23c', relay:'#9254de', team_confrontation:'#f56c6c' }
const eventColor = t => eventColors[t] || '#909399'
const statusLabel = s => ({ preparing:'筹备中', registration:'报名中', ongoing:'进行中', finished:'已结束' })[s] || s

async function loadEvents() {
  if (!filterMeet.value) return
  loading.value = true
  const [evRes, regRes] = await Promise.all([
    eventApi.list({ sports_meet: filterMeet.value, page_size: 200 }),
    registrationApi.list({ sports_meet: filterMeet.value, class_name: auth.user?.class_name })
  ])
  events.value = evRes.results || evRes
  const counts = {}
  ;(regRes.results || regRes).forEach(r => {
    if (r.status !== 'cancelled') counts[r.event] = (counts[r.event] || 0) + 1
  })
  classRegCounts.value = counts
  loading.value = false
}

onMounted(async () => {
  const res = await meetApi.list()
  meets.value = (res.results || res).filter(m => m.status !== 'preparing')
  if (meets.value.length) {
    const reg = meets.value.find(m => m.status === 'registration')
    const ongoing = meets.value.find(m => m.status === 'ongoing')
    filterMeet.value = (reg || ongoing || meets.value[0]).id
    loadEvents()
  }
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.event-card { cursor: pointer; width: 240px; transition: transform 0.15s; }
.event-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.event-name { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 4px; }
.event-meta { font-size: 12px; color: #909399; margin-bottom: 2px; }
.event-info { font-size: 12px; color: #606266; line-height: 1.6; }
</style>
