<template>
  <div>
    <el-page-header content="赛程安排" @back="$router.push(`/admin/meets/${meetId}`)" style="margin-bottom:20px" />
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <el-select v-model="filterEvent" placeholder="筛选项目" clearable style="width:200px" @change="load">
            <el-option v-for="e in events" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
          <el-button type="primary" :icon="Plus" @click="openDialog()">新增赛程</el-button>
        </div>
      </template>
      <el-table :data="schedules" v-loading="loading">
        <el-table-column prop="event" label="项目" width="160">
          <template #default="{ row }">{{ eventName(row.event) }}</template>
        </el-table-column>
        <el-table-column prop="stage" label="阶段" width="100" align="center">
          <template #default="{ row }">{{ stageLabel(row.stage) }}</template>
        </el-table-column>
        <el-table-column prop="group_number" label="组次" width="80" align="center">
          <template #default="{ row }">第{{ row.group_number }}组</template>
        </el-table-column>
        <el-table-column prop="scheduled_time" label="比赛时间" width="170" />
        <el-table-column prop="venue" label="场地" min-width="120" />
        <el-table-column prop="notes" label="备注" min-width="120" />
        <el-table-column label="操作" width="130" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="deleteSch(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑赛程' : '新增赛程'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="比赛项目" prop="event">
          <el-select v-model="form.event" style="width:100%">
            <el-option v-for="e in events" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="阶段">
              <el-select v-model="form.stage" style="width:100%">
                <el-option label="初赛" value="preliminary" />
                <el-option label="半决赛" value="semifinal" />
                <el-option label="决赛" value="final" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="组次">
              <el-input-number v-model="form.group_number" :min="1" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="比赛时间">
          <el-date-picker v-model="form.scheduled_time" type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="场地">
          <el-input v-model="form.venue" placeholder="如：田径场跑道1-4道" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
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
import { scheduleApi, eventApi } from '@/api'

const route = useRoute()
const meetId = route.params.id
const schedules = ref([])
const events = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editId = ref(null)
const formRef = ref()
const filterEvent = ref('')

const stageMap = { preliminary:'初赛', semifinal:'半决赛', final:'决赛' }
const stageLabel = s => stageMap[s] || s
const eventName = id => events.value.find(e => e.id === id)?.name || id

const defaultForm = () => ({ event: '', stage: 'final', group_number: 1, scheduled_time: '', venue: '', notes: '' })
const form = reactive(defaultForm())
const rules = { event: [{ required: true, message: '请选择项目' }] }

async function load() {
  loading.value = true
  const params = { sports_meet: meetId }
  if (filterEvent.value) params.event = filterEvent.value
  const res = await scheduleApi.list(params)
  schedules.value = res.results || res
  loading.value = false
}

function openDialog(row) {
  editId.value = row?.id || null
  if (row) Object.assign(form, row)
  else Object.assign(form, defaultForm())
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (editId.value) {
      await scheduleApi.update(editId.value, form)
      ElMessage.success('更新成功')
    } else {
      await scheduleApi.create(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function deleteSch(row) {
  await ElMessageBox.confirm('确认删除此赛程？', '提示', { type: 'warning' })
  await scheduleApi.delete(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(async () => {
  const res = await eventApi.list({ sports_meet: meetId })
  events.value = res.results || res
  load()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
