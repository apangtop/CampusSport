<template>
  <div>
    <el-page-header content="成绩管理" @back="$router.push(`/admin/meets/${meetId}`)" style="margin-bottom:20px" />

    <!-- 运动会状态不允许查看成绩 -->
    <el-alert v-if="meetStatus === 'preparing' || meetStatus === 'registration'"
      :title="`当前运动会状态为「${statusLabel(meetStatus)}」，不能查看成绩`"
      type="warning" :closable="false" show-icon style="margin-bottom:16px" />

    <el-card shadow="never" v-if="meetStatus === 'ongoing' || meetStatus === 'finished'">
      <template #header>
        <div class="card-header">
          <div style="display:flex;gap:12px;align-items:center">
            <el-select v-model="filterType" placeholder="项目分类" style="width:110px">
              <el-option label="全部" value="" />
              <el-option v-if="availTypes.has('track')" label="径赛" value="track" />
              <el-option v-if="availTypes.has('field')" label="田赛" value="field" />
              <el-option v-if="availTypes.has('relay')" label="接力" value="relay" />
            </el-select>
            <ClassSelector v-model="filterClass" :clearable="true" :year-filter="true" style="margin-left:0" />
            <el-select v-model="filterEvent" placeholder="选择项目" style="width:220px">
              <el-option v-for="e in filteredEvents" :key="e.id" :label="`${e.name}（${e._scored || 0}/${e._total || 0}）`" :value="e.id" />
            </el-select>
            <el-select v-model="filterStage" placeholder="阶段" style="width:120px">
              <el-option label="决赛" value="final" />
              <el-option v-if="currentEvent && currentEvent.stage_type !== 'single'" label="初赛" value="preliminary" />
            </el-select>
            <el-select v-model="filterComplete" placeholder="录入状态" style="width:130px">
              <el-option label="全部项目" value="" />
              <el-option label="已全部录入" value="complete" />
              <el-option label="未全部录入" value="incomplete" />
            </el-select>
            <el-select v-model="filterGroup" placeholder="组次" style="width:110px" clearable>
              <el-option label="全部组" value="" />
              <el-option v-for="g in groups" :key="g.key" :label="`第${g.group}组`" :value="g.key" />
            </el-select>
            <el-tag type="info">
              {{ enteredCount }}/{{ allRows.length }} 已录入
            </el-tag>
          </div>
          <div style="display:flex;gap:8px">
            <el-button v-if="isAdvancementStage" type="success" @click="autoAdvance" :disabled="!filterEvent">
              拉通晋级
            </el-button>
            <el-button v-if="isAdvancementStage" type="warning" @click="confirmAdvance" :disabled="!selectedRegistrations.length">
              手动晋级（{{ selectedRegistrations.length }} 人）
            </el-button>
            <el-button @click="calcRanks" :disabled="!filterEvent">重新计算排名</el-button>
          </div>
        </div>
      </template>
      <!-- 排序切换 -->
      <div style="margin-bottom:12px;display:flex;align-items:center;gap:8px">
        <el-radio-group v-model="sortMode" size="small" @change="loadAll">
          <el-radio-button value="group">按组排列</el-radio-button>
          <el-radio-button value="rank">拉通排名</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 按组排列 -->
      <template v-if="sortMode === 'group'">
        <div v-for="grp in groupedRows" :key="grp.key" style="margin-bottom:20px">
          <h4 style="margin:0 0 8px;color:#303133">
            {{ stageNameMap[grp.stage] || grp.stage }} 第{{ grp.group }}组
            <el-tag size="small" type="info" style="margin-left:8px">{{ grp.entered }}/{{ grp.rows.length }} 已录入</el-tag>
          </h4>
          <el-table :data="grp.rows" size="small" @selection-change="grp.selected = $event">
            <el-table-column v-if="isAdvancementStage" type="selection" width="50" align="center" />
            <el-table-column v-if="currentEvent && needsLanes(currentEvent.event_type)" label="道次" width="55" align="center">
              <template #default="{ row }">{{ row.lane || '-' }}</template>
            </el-table-column>
            <el-table-column label="录入" width="70" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.hasScore" type="success" size="small">已录</el-tag>
                <el-tag v-else type="danger" size="small">未录</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="排名" width="60" align="center">
              <template #default="{ row }">
                <span v-if="row.rank === 1">🥇</span>
                <span v-else-if="row.rank === 2">🥈</span>
                <span v-else-if="row.rank === 3">🥉</span>
                <span v-else-if="row.rank">第{{ row.rank }}名</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="student_name" label="姓名" width="90" />
            <el-table-column prop="class_name" label="班级" width="110" />
            <el-table-column label="成绩" width="110" align="center">
              <template #default="{ row }">{{ row.result || '-' }}</template>
            </el-table-column>
            <el-table-column label="积分" width="55" align="center">
              <template #default="{ row }">{{ row.points || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="130" align="center">
              <template #default="{ row }">
                <template v-if="row.hasScore">
                  <el-button link type="primary" @click="editScore(row)">编辑</el-button>
                  <el-button link type="danger" @click="deleteScore(row)">删除</el-button>
                </template>
                <el-button v-else link type="success" @click="quickAdd(row)">录入</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>

      <!-- 拉通排名 -->
      <el-table v-else :data="flatRows" v-loading="loading" @selection-change="onSelectionChange">
        <el-table-column v-if="isAdvancementStage" type="selection" width="50" align="center" />
        <el-table-column label="组次" width="90" align="center">
          <template #default="{ row }">第{{ row._group }}组</template>
        </el-table-column>
        <el-table-column v-if="currentEvent && needsLanes(currentEvent.event_type)" label="道次" width="55" align="center">
          <template #default="{ row }">{{ row.lane || '-' }}</template>
        </el-table-column>
        <el-table-column label="录入" width="70" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.hasScore" type="success" size="small">已录</el-tag>
            <el-tag v-else type="danger" size="small">未录</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="名次" width="60" align="center">
          <template #default="{ row }">
            <span v-if="row.rank === 1">🥇</span>
            <span v-else-if="row.rank === 2">🥈</span>
            <span v-else-if="row.rank === 3">🥉</span>
            <span v-else-if="row.rank">第{{ row.rank }}名</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="student_name" label="姓名" width="90" />
        <el-table-column prop="class_name" label="班级" width="110" />
        <el-table-column label="成绩" width="110" align="center">
          <template #default="{ row }">{{ row.result || '-' }}</template>
        </el-table-column>
        <el-table-column label="积分" width="55" align="center">
          <template #default="{ row }">{{ row.points || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" align="center">
          <template #default="{ row }">
            <template v-if="row.hasScore">
              <el-button link type="primary" @click="editScore(row)">编辑</el-button>
              <el-button link type="danger" @click="deleteScore(row)">删除</el-button>
            </template>
            <el-button v-else link type="success" @click="quickAdd(row)">录入</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 录入/编辑弹窗 -->
      <el-dialog v-model="editVisible" :title="editRow?.hasScore ? '编辑成绩' : '录入成绩'" width="360px">
        <el-form label-width="80px" v-if="editRow">
          <el-form-item label="姓名"><strong>{{ editRow.student_name }}</strong></el-form-item>
          <el-form-item label="班级">{{ editRow.class_name }}</el-form-item>
          <el-form-item label="成绩">
            <el-input v-model="editResult" @keyup.enter="saveEdit" :placeholder="currentUnit" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="editVisible = false">取消</el-button>
          <el-button type="primary" @click="saveEdit">保存</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { scoreApi, eventApi, meetApi } from '@/api'
import { shortDatetime, needsLanes } from '@/utils/format'

const route = useRoute()
const meetId = route.params.id
const events = ref([])
const loading = ref(false)
const filterEvent = ref('')
const filterStage = ref('final')
const filterClass = ref('')
const filterComplete = ref('')
const filterType = ref('')
const filterGroup = ref('')
const sortMode = ref('group')
const meetStatus = ref('')
const summaryMap = ref({})  // event_id → { total, scored, complete }
const allRows = ref([])     // 原始数据
const groups = ref([])      // [{key, group, stage}]

const stageNameMap = { preliminary:'初赛', final:'决赛' }

const availTypes = computed(() => {
  const s = new Set()
  events.value.forEach(e => s.add(e.event_type))
  return s
})

const filteredEvents = computed(() => {
  let list = events.value
  if (filterType.value) {
    list = list.filter(e => e.event_type === filterType.value)
  }
  if (filterClass.value && filterClass.value.endsWith('级')) {
    list = list.filter(e => e.grade === filterClass.value)
  }
  if (filterComplete.value) {
    list = list.filter(e => {
      const s = summaryMap.value[e.id]
      return s && (filterComplete.value === 'complete' ? s.complete : !s.complete)
    })
  }
  return list
})

const statusMap = { preparing:'筹备中', registration:'报名中', ongoing:'进行中', finished:'已结束' }
const statusLabel = s => statusMap[s] || s

const selectedRegistrations = ref([])
const isAdvancementStage = computed(() =>
  filterStage.value === 'preliminary'
)

const enteredCount = computed(() => allRows.value.filter(r => r.hasScore).length)
const currentEvent = computed(() => events.value.find(e => e.id == filterEvent.value))
const currentUnit = computed(() => {
  const u = currentEvent.value?.result_unit
  return { second:'秒', meter:'米', count:'次', rank:'名次' }[u] || ''
})

function onSelectionChange(vals) {
  selectedRegistrations.value = vals.filter(r => r.hasScore)
}

async function autoAdvance() {
  try {
    const result = await ElMessageBox.prompt('拉通排名取前几名晋级？', '自动晋级', {
      confirmButtonText: '确定晋级',
      inputValue: '6',
      inputPattern: /^\d+$/,
      inputErrorMessage: '请输入数字'
    })
    const count = parseInt(result.value) || 6
    const res = await scoreApi.autoAdvanceTop({
      event_id: filterEvent.value,
      stage: filterStage.value,
      advance_count: count
    })
    ElMessage.success(res.detail)
    loadAll()
  } catch {}
}

async function confirmAdvance() {
  try {
    const regIds = selectedRegistrations.value.map(r => r.registration_id)
    await scoreApi.confirmAdvancement({
      event_id: filterEvent.value,
      stage: filterStage.value,
      registration_ids: regIds
    })
    ElMessage.success('晋级名单已确认')
    selectedRegistrations.value = []
    loadAll()
  } catch {}
}

const editVisible = ref(false)
const editRow = ref(null)
const editResult = ref('')

function editScore(row) {
  editRow.value = row
  editResult.value = row.result || ''
  editVisible.value = true
}

function quickAdd(row) {
  editRow.value = row
  editResult.value = ''
  editVisible.value = true
}

async function saveEdit() {
  try {
    if (editRow.value.hasScore && editRow.value.scoreId) {
      await scoreApi.update(editRow.value.scoreId, {
        result: editResult.value,
        result_numeric: parseFloat(editResult.value) || null
      })
    } else {
      await scoreApi.create({
        registration: editRow.value.registration_id,
        stage: filterStage.value,
        result: editResult.value,
        result_numeric: parseFloat(editResult.value) || null
      })
    }
    ElMessage.success('保存成功')
    editVisible.value = false
    loadAll()
  } catch {}
}

async function deleteScore(row) {
  try {
    await ElMessageBox.confirm(`确认删除 ${row.student_name} 的成绩？`, '提示', { type: 'warning' })
    await scoreApi.delete(row.scoreId)
    ElMessage.success('已删除')
    loadAll()
  } catch {}
}

async function loadCompletion() {
  try {
    const res = await meetApi.scoreSummary(meetId, { stage: filterStage.value })
    const map = {}
    ;(res || []).forEach(s => {
      map[s.event_id] = { total: s.total, scored: s.scored, complete: s.complete }
    })
    summaryMap.value = map
    // 将统计数据合并到 events，用于下拉框显示
    events.value.forEach(e => {
      e._total = map[e.id]?.total || 0
      e._scored = map[e.id]?.scored || 0
    })
  } catch {}
}

// 任一筛选变化 → 重新加载
watch([filterType, filterClass, filterStage, filterComplete], async () => {
  if (filterClass.value && filterClass.value.endsWith('级')) {
    filterEvent.value = ''
  }
  await loadCompletion()
  if (!filterEvent.value && filteredEvents.value.length) {
    filterEvent.value = filteredEvents.value[0].id
  }
  loadAll()
})

watch(filterEvent, () => {
  const ev = currentEvent.value
  if (ev && ev.stage_type === 'single') {
    filterStage.value = 'final'
  }
  loadAll()
})

async function loadAll() {
  if (!filterEvent.value) return
  loading.value = true
  const [partRes, scoreRes] = await Promise.all([
    eventApi.participants(filterEvent.value),
    scoreApi.list({ event: filterEvent.value, stage: filterStage.value })
  ])
  const participants = partRes.results || partRes
  const scores = scoreRes.results || scoreRes
  const scoreMap = {}
  scores.forEach(s => { scoreMap[s.registration] = s })

  const raw = participants.map(p => {
    const s = scoreMap[p.id]
    return {
      registration_id: p.id,
      student_name: p.student?.name || '',
      class_name: p.student?.class_name || '',
      lane: p.lane || 0,
      schedule_info: p.schedule_info,
      hasScore: !!s,
      scoreId: s?.id,
      result: s?.result || '',
      result_numeric: s?.result_numeric,
      rank: s?.rank,
      points: s?.points,
      is_advanced: s?.is_advanced,
      registration: p.id
    }
  }).filter(r => {
    if (!filterClass.value) return true
    return r.class_name === filterClass.value
  })

  // 提取组次列表
  const groupSet = new Map()
  raw.forEach(r => {
    const si = r.schedule_info
    if (si) {
      const key = `${si.stage}-${si.group_number}`
      if (!groupSet.has(key)) groupSet.set(key, { key, stage: si.stage, group: si.group_number })
    }
  })
  groups.value = Array.from(groupSet.values())
    .sort((a, b) => a.group - b.group)

  allRows.value = raw
  loading.value = false
}

const groupedRows = computed(() => {
  const grpMap = {}
  allRows.value.forEach(r => {
    const si = r.schedule_info
    const key = si ? `${si.stage}-${si.group_number}` : 'unassigned'
    if (!grpMap[key]) {
      grpMap[key] = {
        key,
        stage: si?.stage || 'final',
        group: si?.group_number || 1,
        rows: [],
        entered: 0
      }
    }
    grpMap[key].rows.push(r)
    if (r.hasScore) grpMap[key].entered++
  })
  // 组内按道次排序
  const result = Object.values(grpMap)
  result.forEach(g => g.rows.sort((a, b) => (a.lane || 999) - (b.lane || 999)))
  result.sort((a, b) => a.group - b.group)
  // 组次筛选
  if (filterGroup.value) return result.filter(g => g.key === filterGroup.value)
  return result
})

const flatRows = computed(() => {
  // 拉通排名：按成绩排序
  return [...allRows.value].sort((a, b) => {
    if (a.hasScore && b.hasScore) {
      if (a.rank && b.rank) return a.rank - b.rank
      return (a.rank || 999) - (b.rank || 999)
    }
    if (a.hasScore) return -1
    if (b.hasScore) return 1
    return (a.lane || 999) - (b.lane || 999)
  })
})

async function calcRanks() {
  await scoreApi.calculateRanks({ event_id: filterEvent.value, stage: filterStage.value })
  ElMessage.success('排名已重新计算')
  loadAll()
}

onMounted(async () => {
  try {
    const [evRes, meet] = await Promise.all([
      eventApi.list({ sports_meet: meetId, page_size: 200 }),
      meetApi.get(meetId).catch(() => null)
    ])
    events.value = evRes.results || evRes
    meetStatus.value = meet?.status || ''
    await loadCompletion()
    if (events.value.length) {
      filterEvent.value = filteredEvents.value[0]?.id
      if (meetStatus.value === 'ongoing' || meetStatus.value === 'finished') {
        loadAll()
      }
    }
  } catch (e) {
    console.error('加载失败', e)
  }
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
