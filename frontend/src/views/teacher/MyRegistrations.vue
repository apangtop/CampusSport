<template>
  <div>
    <!-- 顶部统计卡片 -->
    <el-row :gutter="12" style="margin-bottom:16px">
      <el-col :xs="6" :sm="6" v-for="card in statCards" :key="card.label">
        <el-card shadow="hover" :body-style="{ padding: '12px' }">
          <div style="text-align:center">
            <div style="font-size:24px;font-weight:700" :style="{ color: card.color }">{{ card.value }}</div>
            <div style="font-size:12px;color:#909399;margin-top:2px">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 个人项目报名明细 -->
      <el-col :xs="24" :md="16" style="margin-bottom:16px">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>个人项目报名明细</span>
              <div style="display:flex;gap:8px">
                <el-select v-model="filterType" placeholder="类型" clearable style="width:90px" @change="load">
                  <el-option label="全部" value="" /><el-option label="径赛" value="track" /><el-option label="田赛" value="field" />
                </el-select>
                <el-select v-model="filterFull" placeholder="报名状态" clearable style="width:110px">
                  <el-option label="全部" value="" /><el-option label="未报满" value="open" /><el-option label="已满" value="full" /><el-option label="未报名" value="empty" />
                </el-select>
                <el-select v-model="filterMeet" placeholder="选择运动会" style="width:200px" @change="load">
                  <el-option v-for="m in meets" :key="m.id" :label="m.name" :value="m.id" />
                </el-select>
              </div>
            </div>
          </template>

          <!-- 按项目分组卡片 -->
          <div v-if="eventGroups.length" style="display:flex;flex-direction:column;gap:12px">
            <div v-for="grp in eventGroups" :key="grp.event_id" style="border:1px solid #ebeef5;border-radius:8px;padding:12px">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <div>
                  <strong>{{ grp.event_name }}</strong>
                  <el-tag size="small" style="margin-left:8px" :type="grp.type === 'track' ? '' : 'success'">
                    {{ typeLabel(grp.type) }}
                  </el-tag>
                </div>
                <div style="display:flex;align-items:center;gap:8px">
                  <!-- 进度条 -->
                  <div style="width:120px">
                    <div style="font-size:11px;color:#909399;margin-bottom:2px;display:flex;justify-content:space-between">
                      <span>{{ grp.approved }}/{{ grp.max }} 已审核</span>
                      <span v-if="grp.pending">+{{ grp.pending }} 待审</span>
                    </div>
                    <el-progress :percentage="Math.round(grp.approved / grp.max * 100)" :color="grp.approved >= grp.max ? '#67c23a' : '#409eff'" :stroke-width="8" />
                  </div>
                  <el-tag v-if="grp.approved >= grp.max" type="success" size="small">已满</el-tag>
                  <el-tag v-else-if="grp.total === 0" type="info" size="small">未报</el-tag>
                </div>
              </div>
              <!-- 学生名单 -->
              <div v-if="grp.students.length" style="display:flex;flex-wrap:wrap;gap:4px">
                <el-tag v-for="r in grp.students" :key="r.id" size="small"
                  :type="r.status === 'approved' ? 'success' : r.status === 'rejected' ? 'danger' : 'warning'"
                  :effect="r.status === 'approved' ? 'light' : 'plain'"
                  style="cursor:pointer"
                  @click="showRegDetail(r)">
                  {{ r.student_name }}
                </el-tag>
              </div>
              <span v-else style="color:#c0c4cc;font-size:12px">尚未报名</span>
            </div>
          </div>
          <el-empty v-else description="请选择运动会查看报名情况" :image-size="60" />
        </el-card>
      </el-col>

      <!-- 团体项目 + 快捷统计 -->
      <el-col :xs="24" :md="8" style="margin-bottom:16px">
        <el-card shadow="never" style="margin-bottom:12px">
          <template #header><span>团体项目</span></template>
          <div v-if="teamRegs.length">
            <div v-for="t in teamRegs" :key="t.id" style="padding:8px 0;border-bottom:1px solid #f0f0f0">
              <div style="font-weight:600;font-size:13px">{{ t.event_name || '团体项目' }}</div>
              <div style="font-size:12px;color:#909399">
                {{ (t.members_detail || []).map(m => m.name).join('、') || '-' }}
              </div>
              <el-tag :type="t.status === 'approved' ? 'success' : 'warning'" size="small" style="margin-top:4px">
                {{ t.status === 'approved' ? '已审核' : '待审核' }}
              </el-tag>
            </div>
          </div>
          <el-empty v-else description="暂无团体报名" :image-size="40" />
        </el-card>

        <el-card shadow="never">
          <template #header><span>快捷操作</span></template>
          <div style="display:flex;flex-direction:column;gap:8px">
            <el-button @click="$router.push('/teacher/register')">去报名</el-button>
            <el-button @click="$router.push('/teacher/events')">浏览项目</el-button>
            <el-button @click="$router.push('/teacher/students')">管理学生</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { registrationApi, teamRegistrationApi, meetApi, eventApi } from '@/api'

const auth = useAuthStore()
const meets = ref([])
const regs = ref([])
const teamRegs = ref([])
const events = ref([])
const loading = ref(false)
const filterMeet = ref('')
const filterType = ref('')
const filterFull = ref('')

const typeLabel = t => ({ track:'径赛', field:'田赛', relay:'接力' })[t] || t

const statCards = computed(() => {
  const list = regs.value
  return [
    { label: '报名项数', value: list.filter(r => r.status !== 'cancelled').length, color: '#1a6db5' },
    { label: '已审核', value: list.filter(r => r.status === 'approved').length, color: '#67c23a' },
    { label: '待审核', value: list.filter(r => r.status === 'submitted').length, color: '#e6a23c' },
    { label: '已拒绝', value: list.filter(r => r.status === 'rejected').length, color: '#f56c6c' },
  ]
})

// 按项目分组（含未报名项目）
const eventGroups = computed(() => {
  const map = {}
  // 先初始化所有个人项目
  events.value.filter(e => !['relay', 'team_confrontation'].includes(e.event_type)).forEach(ev => {
    map[ev.id] = {
      event_id: ev.id,
      event_name: ev.name,
      type: ev.event_type,
      max: ev.max_per_class || 0,
      total: 0, approved: 0, pending: 0, rejected: 0,
      students: []
    }
  })
  // 填入报名数据
  regs.value.forEach(r => {
    if (!map[r.event]) return
    map[r.event].total++
    if (r.status === 'approved') map[r.event].approved++
    else if (r.status === 'submitted') map[r.event].pending++
    else if (r.status === 'rejected') map[r.event].rejected++
    map[r.event].students.push(r)
  })

  let list = Object.values(map)

  // 类型筛选
  if (filterType.value) list = list.filter(g => g.type === filterType.value)
  // 报名状态筛选
  if (filterFull.value === 'open') list = list.filter(g => g.approved < g.max)
  else if (filterFull.value === 'full') list = list.filter(g => g.approved >= g.max)
  else if (filterFull.value === 'empty') list = list.filter(g => g.total === 0)

  return list.sort((a, b) => {
    if (a.approved < a.max && b.approved >= b.max) return -1
    if (a.approved >= a.max && b.approved < b.max) return 1
    return b.total - a.total
  })
})

function showRegDetail(r) {
  // 简单提示
}

async function load() {
  loading.value = true
  const params = { class_name: auth.user?.class_name }
  if (filterMeet.value) params.sports_meet = filterMeet.value
  const [regRes, teamRes, evRes] = await Promise.all([
    registrationApi.list({ ...params, page_size: 200 }),
    teamRegistrationApi.list({ class_name: auth.user?.class_name, ...(filterMeet.value ? { sports_meet: filterMeet.value } : {}), page_size: 200 }),
    filterMeet.value ? eventApi.list({ sports_meet: filterMeet.value, page_size: 200 }) : Promise.resolve({ results: [] })
  ])
  regs.value = regRes.results || regRes
  teamRegs.value = teamRes.results || teamRes
  events.value = evRes.results || evRes
  loading.value = false
}

onMounted(async () => {
  const res = await meetApi.list()
  meets.value = res.results || res
  const reg = meets.value.find(m => m.status === 'registration')
  const ongoing = meets.value.find(m => m.status === 'ongoing')
  filterMeet.value = (reg || ongoing || meets.value[0])?.id
  if (filterMeet.value) load()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
</style>
