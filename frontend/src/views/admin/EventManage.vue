<template>
  <div>
    <el-page-header content="项目管理" @back="$router.push(`/admin/meets/${meetId}`)" style="margin-bottom:20px" />
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>比赛项目列表</span>
          <div style="display:flex;gap:12px">
            <el-select v-model="filterType" clearable placeholder="项目类型" style="width:130px" @change="load">
              <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
            <el-button type="primary" :icon="Plus" @click="openDialog()">新建项目</el-button>
          </div>
        </div>
      </template>
      <el-table :data="events" v-loading="loading">
        <el-table-column prop="name" label="项目名称" min-width="130" />
        <el-table-column prop="event_type" label="类型" width="100" align="center">
          <template #default="{ row }">{{ typeLabel(row.event_type) }}</template>
        </el-table-column>
        <el-table-column prop="gender" label="性别" width="70" align="center">
          <template #default="{ row }">{{ genderLabel(row.gender) }}</template>
        </el-table-column>
        <el-table-column prop="result_unit" label="成绩单位" width="90" align="center">
          <template #default="{ row }">{{ unitLabel(row.result_unit) }}</template>
        </el-table-column>
        <el-table-column prop="stage_type" label="赛制" width="130" align="center">
          <template #default="{ row }">{{ stageLabel(row.stage_type) }}</template>
        </el-table-column>
        <el-table-column prop="max_per_class" label="班级上限" width="90" align="center" />
        <el-table-column prop="referee_name" label="负责裁判" width="100" />
        <el-table-column prop="registration_count" label="已报名" width="80" align="center" />
        <el-table-column label="操作" width="140" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="deleteEvent(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑项目' : '新建项目'" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="如：男子100米" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="项目类型" prop="event_type">
              <el-select v-model="form.event_type" style="width:100%">
                <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="参赛性别">
              <el-select v-model="form.gender" style="width:100%">
                <el-option label="男" value="male" />
                <el-option label="女" value="female" />
                <el-option label="混合" value="mixed" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="成绩单位">
              <el-select v-model="form.result_unit" style="width:100%">
                <el-option label="秒" value="second" />
                <el-option label="米" value="meter" />
                <el-option label="次" value="count" />
                <el-option label="名次" value="rank" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="赛制">
              <el-select v-model="form.stage_type" style="width:100%">
                <el-option label="直接决赛" value="single" />
                <el-option label="两阶段(初赛+决赛)" value="two" />
                <el-option label="三阶段" value="three" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12" v-if="form.stage_type !== 'single'">
          <el-col :span="12">
            <el-form-item label="每组晋级人数">
              <el-input-number v-model="form.advance_per_group" :min="1" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="通配名额">
              <el-input-number v-model="form.advance_wildcard" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="每班报名上限">
          <el-input-number v-model="form.max_per_class" :min="1" style="width:180px" />
          <span style="margin-left:8px;color:#888;font-size:13px">人（本班在此项目最多报名人数）</span>
        </el-form-item>
        <el-form-item label="负责裁判">
          <el-select v-model="form.referee" placeholder="选择裁判" clearable style="width:100%">
            <el-option v-for="r in referees" :key="r.id" :label="r.real_name || r.username" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="积分倍数" v-if="form.event_type?.includes('team') || form.event_type === 'relay'">
          <el-input-number v-model="form.score_multiplier" :min="1" :step="0.5" style="width:180px" />
        </el-form-item>
        <el-form-item label="积分规则">
          <div class="score-rules">
            <div v-for="rank in 6" :key="rank" class="rule-row">
              <span class="rule-rank">第{{ rank }}名</span>
              <el-input-number v-model="scoreRules[rank]" :min="0" size="small" style="width:100px" />
              <span class="rule-unit">分</span>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { eventApi, userApi } from '@/api'

const route = useRoute()
const meetId = route.params.id
const events = ref([])
const referees = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editId = ref(null)
const formRef = ref()
const filterType = ref('')

const defaultScoreRules = () => ({ 1: 7, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1 })
const scoreRules = reactive(defaultScoreRules())

const typeOptions = [
  { label: '径赛', value: 'track' }, { label: '田赛', value: 'field' },
  { label: '趣味个人', value: 'fun_individual' }, { label: '对抗团体', value: 'team_confrontation' },
  { label: '接力团体', value: 'relay' }
]
const typeMap = { track:'径赛', field:'田赛', fun_individual:'趣味个人', team_confrontation:'对抗团体', relay:'接力团体' }
const typeLabel = t => typeMap[t] || t
const genderMap = { male:'男', female:'女', mixed:'混合' }
const genderLabel = g => genderMap[g] || g
const unitMap = { second:'秒', meter:'米', count:'次', rank:'名次' }
const unitLabel = u => unitMap[u] || u
const stageMap = { single:'直接决赛', two:'两阶段(初赛+决赛)', three:'三阶段' }
const stageLabel = s => stageMap[s] || s

const defaultForm = () => ({
  sports_meet: meetId, name: '', event_type: 'track', gender: 'male',
  result_unit: 'second', stage_type: 'single', advance_per_group: 2,
  advance_wildcard: 1, max_per_class: 2,
  team_size: 0, referee: null, score_multiplier: 1.0, score_rules: {}
})
const form = reactive(defaultForm())
const rules = {
  name: [{ required: true, message: '请输入项目名称' }],
  event_type: [{ required: true, message: '请选择项目类型' }]
}

async function load() {
  loading.value = true
  const params = { sports_meet: meetId }
  if (filterType.value) params.type = filterType.value
  const res = await eventApi.list(params)
  events.value = res.results || res
  loading.value = false
}

function openDialog(row) {
  editId.value = row?.id || null
  if (row) {
    Object.assign(form, row)
    const rules = row.score_rules && Object.keys(row.score_rules).length ? row.score_rules : defaultScoreRules()
    Object.assign(scoreRules, rules)
  } else {
    Object.assign(form, defaultForm())
    Object.assign(scoreRules, defaultScoreRules())
  }
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    const data = { ...form, sports_meet: meetId, score_rules: { ...scoreRules } }
    if (editId.value) {
      await eventApi.update(editId.value, data)
      ElMessage.success('更新成功')
    } else {
      await eventApi.create(data)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function deleteEvent(row) {
  await ElMessageBox.confirm(`确认删除「${row.name}」？`, '提示', { type: 'warning' })
  await eventApi.delete(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(async () => {
  load()
  const res = await userApi.list({ role: 'referee' })
  referees.value = res.results || res
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.score-rules { display: flex; flex-direction: column; gap: 8px; }
.rule-row { display: flex; align-items: center; gap: 8px; }
.rule-rank { width: 50px; font-size: 13px; }
.rule-unit { font-size: 13px; color: #888; }
</style>
