<template>
  <div>
    <el-page-header content="赛程安排" @back="$router.push(`/admin/meets/${meetId}`)" style="margin-bottom:20px" />

    <!-- 按项目类型分组展示，点击弹出详情 -->
    <el-card shadow="never">
      <template #header>
        <span>比赛项目列表（点击项目查看/编辑赛程）</span>
      </template>
      <div v-for="group in groupedEvents" :key="group.label" style="margin-bottom:16px">
        <h4 style="margin:0 0 8px;color:#606266">{{ group.label }}</h4>
        <div style="display:flex;flex-wrap:wrap;gap:8px">
          <el-card
            v-for="ev in group.events" :key="ev.id"
            class="event-card" shadow="hover"
            :style="{ borderTop: `3px solid ${eventColor(ev.event_type)}` }"
            @click="openEventDetail(ev)"
          >
            <div class="event-name">{{ ev.name }}</div>
            <div class="event-meta">
              {{ genderLabel(ev.gender) }}
              <el-tag v-if="ev.grade" size="small" type="warning" style="margin-left:4px">{{ ev.grade }}</el-tag>
            </div>
            <div class="event-info-line">👤 {{ ev.referee_name || '未分配' }}</div>
            <div class="event-info-line">📋 {{ regLabel(ev) }}</div>
            <el-progress :percentage="progressPct(ev)" :stroke-width="6" :show-text="false"
              :color="progressPct(ev) >= 100 ? '#67c23a' : '#409eff'" style="margin-top:4px" />
          </el-card>
        </div>
      </div>
    </el-card>

    <!-- 项目赛程详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="detailEvent?.name || '赛程详情'" width="800px" top="3vh">
      <!-- 项目信息 -->
      <el-descriptions v-if="detailEvent" :column="3" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="类型">{{ typeLabel(detailEvent.event_type) }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ genderLabel(detailEvent.gender) }}</el-descriptions-item>
        <el-descriptions-item label="年级">{{ detailEvent.grade || '全校混赛' }}</el-descriptions-item>
        <el-descriptions-item label="赛制">{{ stageTypeLabel(detailEvent.stage_type) }}</el-descriptions-item>
        <el-descriptions-item label="成绩单位">{{ unitLabel(detailEvent.result_unit) }}</el-descriptions-item>
        <el-descriptions-item label="已报名">{{ participants.length || detailEvent.registration_count || 0 }} 人</el-descriptions-item>
      </el-descriptions>

      <!-- 参赛名单 -->
      <div style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:8px">
          {{ isTeamEvent ? '参赛队伍' : '参赛学生' }}
        </div>
        <div v-if="participants.length && !isTeamEvent" style="display:flex;flex-wrap:wrap;gap:4px;max-height:120px;overflow-y:auto">
          <el-tag v-for="p in participants" :key="p.id" size="small" :type="p.status === 'approved' ? 'success' : 'warning'">
            {{ p.student?.name }}({{ p.student?.class_name }})
            <span v-if="p.lane" style="margin-left:4px;opacity:0.7">{{ needsLanes(detailEvent?.event_type) ? p.lane + '道' : p.lane }}</span>
          </el-tag>
        </div>
        <div v-else-if="participants.length && isTeamEvent">
          <div v-for="t in participants" :key="t.id" style="margin:4px 0">
            <el-tag size="small" :type="t.status === 'approved' ? 'success' : 'warning'" style="margin-right:8px">{{ t.class_name }}</el-tag>
            <el-tag v-for="m in (t.members_detail || [])" :key="m.id" size="small" type="info" style="margin:1px">{{ m.name }}</el-tag>
            <el-tag v-if="t.lane" size="small" type="danger" style="margin-left:4px">{{ t.lane }}道</el-tag>
          </div>
        </div>
        <span v-else style="color:#ccc;font-size:13px">暂无报名</span>
      </div>

      <!-- 赛程列表 -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <span style="font-weight:600">赛程列表</span>
        <el-button type="primary" size="small" @click="openSchDialog()">+ 添加赛程</el-button>
      </div>
      <el-table :data="eventSchedules" size="small" v-loading="schLoading">
        <el-table-column prop="stage" label="阶段" width="90" align="center">
          <template #default="{ row }">{{ stageLabel(row.stage) }}</template>
        </el-table-column>
        <el-table-column label="组次" width="80" align="center">
          <template #default="{ row }">第{{ row.group_number }}组</template>
        </el-table-column>
        <el-table-column label="比赛时间" width="170">
          <template #default="{ row }">
            <span v-if="row.scheduled_time">{{ shortDatetime(row.scheduled_time) }}</span>
            <span v-else style="color:#ccc">待定</span>
          </template>
        </el-table-column>
        <el-table-column prop="venue" label="场地" min-width="120">
          <template #default="{ row }">
            <span v-if="row.venue">{{ row.venue }}</span>
            <span v-else style="color:#ccc">待定</span>
          </template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" width="120" />
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openSchDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="deleteSch(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!eventSchedules.length && !schLoading" description="暂无赛程，点击上方按钮添加" />
    </el-dialog>

    <!-- 赛程编辑弹窗 -->
    <el-dialog v-model="schDialogVisible" :title="schEditId ? '编辑赛程' : '添加赛程'" width="480px">
      <el-form :model="schForm" ref="schFormRef" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="阶段">
              <el-select v-model="schForm.stage" style="width:100%">
                <el-option label="初赛" value="preliminary" />
                <el-option label="决赛" value="final" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="组次">
              <el-input-number v-model="schForm.group_number" :min="1" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="比赛时间">
          <el-date-picker v-model="schForm.scheduled_time" type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="场地">
          <el-input v-model="schForm.venue" placeholder="如：田径场直道" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="schForm.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="schDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="schSaving" @click="saveSch">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { scheduleApi, eventApi } from '@/api'
import { shortDatetime, needsLanes } from '@/utils/format'

const route = useRoute()
const meetId = route.params.id

const eventColors = { track:'#409eff', field:'#67c23a', fun_individual:'#e6a23c', relay:'#9254de', team_confrontation:'#f56c6c' }
function eventColor(type) { return eventColors[type] || '#909399' }
const events = ref([])
const totalSchedules = ref([])  // 所有赛程，用于统计数量
const eventSchedules = ref([])  // 当前选中项目的赛程
const schLoading = ref(false)
const schSaving = ref(false)

const detailVisible = ref(false)
const detailEvent = ref(null)
const participants = ref([])
const isTeamEvent = computed(() => {
  return detailEvent.value && ['relay', 'team_confrontation'].includes(detailEvent.value.event_type)
})

const schDialogVisible = ref(false)
const schEditId = ref(null)
const schFormRef = ref()
const defaultSchForm = () => ({ stage: 'final', group_number: 1, scheduled_time: '', venue: '', notes: '' })
const schForm = reactive(defaultSchForm())

const stageMap = { preliminary:'初赛', semifinal:'半决赛', final:'决赛' }
const stageLabel = s => stageMap[s] || s
const stageTypeMap = { single:'直接决赛', two:'初赛+决赛', three:'初赛+半决赛+决赛' }
const stageTypeLabel = s => stageTypeMap[s] || s
const typeMap = { track:'径赛', field:'田赛', fun_individual:'趣味', relay:'接力', team_confrontation:'对抗' }
const typeLabel = t => typeMap[t] || t
const genderMap = { male:'男', female:'女', mixed:'混合' }
const genderLabel = g => genderMap[g] || g
const unitMap = { second:'秒', meter:'米', count:'次', rank:'名次' }
const unitLabel = u => unitMap[u] || u

const groupedEvents = computed(() => {
  const groups = {}
  for (const e of events.value) {
    const t = e.event_type
    if (!groups[t]) groups[t] = { label: typeLabel(t), events: [] }
    groups[t].events.push(e)
  }
  return Object.values(groups)
})

const scheduleCounts = computed(() => {
  const counts = {}
  totalSchedules.value.forEach(s => {
    counts[s.event] = (counts[s.event] || 0) + 1
  })
  return counts
})

function isTeam(ev) { return ev && ['relay', 'team_confrontation'].includes(ev.event_type) }
function regLabel(ev) {
  const cur = isTeam(ev) ? (ev.team_count || 0) : (ev.registration_count || 0)
  const unit = isTeam(ev) ? '队' : '人'
  return `${cur}/${ev.total_max || 0} ${unit}`
}
function progressPct(ev) {
  const cur = isTeam(ev) ? (ev.team_count || 0) : (ev.registration_count || 0)
  return Math.min(100, Math.round((cur / (ev.total_max || 1)) * 100))
}

async function openEventDetail(ev) {
  detailEvent.value = ev
  detailVisible.value = true
  schLoading.value = true
  const [schRes, partRes] = await Promise.all([
    scheduleApi.list({ event: ev.id }),
    eventApi.participants(ev.id)
  ])
  eventSchedules.value = schRes.results || schRes
  participants.value = partRes.results || partRes
  schLoading.value = false
}

function openSchDialog(row) {
  schEditId.value = row?.id || null
  if (row) {
    schForm.stage = row.stage
    schForm.group_number = row.group_number
    schForm.scheduled_time = row.scheduled_time || ''
    schForm.venue = row.venue || ''
    schForm.notes = row.notes || ''
  } else {
    Object.assign(schForm, defaultSchForm())
  }
  schDialogVisible.value = true
}

async function saveSch() {
  schSaving.value = true
  try {
    const data = { ...schForm, event: detailEvent.value.id }
    if (schEditId.value) {
      await scheduleApi.update(schEditId.value, data)
      ElMessage.success('已更新')
    } else {
      await scheduleApi.create(data)
      ElMessage.success('已添加')
    }
    schDialogVisible.value = false
    // 刷新
    await openEventDetail(detailEvent.value)
    // 同时刷新全局计数
    const all = await scheduleApi.list({ sports_meet: meetId, page_size: 500 })
    totalSchedules.value = all.results || all
  } finally {
    schSaving.value = false
  }
}

async function deleteSch(row) {
  try {
    await ElMessageBox.confirm('确认删除此赛程？', '提示', { type: 'warning' })
    await scheduleApi.delete(row.id)
    ElMessage.success('已删除')
    openEventDetail(detailEvent.value)
    const all = await scheduleApi.list({ sports_meet: meetId, page_size: 500 })
    totalSchedules.value = all.results || all
  } catch {}
}

onMounted(async () => {
  const [evRes, schRes] = await Promise.all([
    eventApi.list({ sports_meet: meetId, page_size: 200 }),
    scheduleApi.list({ sports_meet: meetId, page_size: 500 })
  ])
  events.value = evRes.results || evRes
  totalSchedules.value = schRes.results || schRes
})
</script>

<style scoped>
.event-card {
  cursor: pointer;
  width: 230px;
  transition: transform 0.15s;
}
.event-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.event-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #303133;
}
.event-meta {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.event-info-line {
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
}
</style>
