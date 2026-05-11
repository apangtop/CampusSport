<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">运动会管理</span>
          <el-button type="primary" :icon="Plus" @click="openDialog()">新建运动会</el-button>
        </div>
      </template>
      <el-table :data="meets" v-loading="loading">
        <el-table-column prop="session" label="届次" width="80" align="center">
          <template #default="{ row }">第{{ row.session }}届</template>
        </el-table-column>
        <el-table-column prop="name" label="运动会名称" min-width="160" />
        <el-table-column prop="school" label="学校" width="140" />
        <el-table-column prop="start_date" label="开始日期" width="120" align="center" />
        <el-table-column prop="status" label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="event_count" label="项目数" width="80" align="center" />
        <el-table-column prop="max_events_per_person" label="每人上限" width="90" align="center">
          <template #default="{ row }">{{ row.max_events_per_person }}个项目</template>
        </el-table-column>
        <el-table-column label="操作" width="280" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/admin/meets/${row.id}`)">详情</el-button>
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-dropdown size="small" @command="cmd => setStatus(row, cmd)">
              <el-button link type="warning">状态</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="preparing">筹备中</el-dropdown-item>
                  <el-dropdown-item command="registration">报名中</el-dropdown-item>
                  <el-dropdown-item command="ongoing">进行中</el-dropdown-item>
                  <el-dropdown-item command="finished">已结束</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button link type="danger" @click="deleteMeet(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑运动会' : '新建运动会'" width="540px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="运动会名称" prop="name">
          <el-input v-model="form.name" placeholder="如：春季运动会" />
        </el-form-item>
        <el-form-item label="届次" prop="session">
          <el-input-number v-model="form.session" :min="1" />
        </el-form-item>
        <el-form-item label="学校名称">
          <el-input v-model="form.school" placeholder="学校全称" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="报名截止">
          <el-date-picker v-model="form.registration_deadline" type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="每人项目上限" prop="max_events_per_person">
          <el-input-number v-model="form.max_events_per_person" :min="1" :max="20" />
          <span style="margin-left:8px;color:#888;font-size:13px">个（每名学生最多参加的项目数）</span>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { meetApi } from '@/api'

const meets = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editId = ref(null)
const formRef = ref()

const statusMap = {
  preparing: { label: '筹备中', type: 'info' },
  registration: { label: '报名中', type: 'warning' },
  ongoing: { label: '进行中', type: 'success' },
  finished: { label: '已结束', type: '' }
}
const statusLabel = s => statusMap[s]?.label || s
const statusType = s => statusMap[s]?.type || ''

const form = reactive({
  name: '', session: 1, school: '', start_date: '', end_date: '',
  registration_deadline: '', max_events_per_person: 3, description: ''
})
const rules = {
  name: [{ required: true, message: '请输入运动会名称' }],
  session: [{ required: true, message: '请输入届次' }]
}

async function load() {
  loading.value = true
  const res = await meetApi.list()
  meets.value = res.results || res
  loading.value = false
}

function openDialog(row) {
  editId.value = row?.id || null
  if (row) {
    Object.assign(form, {
      name: row.name, session: row.session, school: row.school || '',
      start_date: row.start_date || '', end_date: row.end_date || '',
      registration_deadline: row.registration_deadline || '',
      max_events_per_person: row.max_events_per_person ?? 3,
      description: row.description || ''
    })
  } else {
    Object.assign(form, { name: '', session: 1, school: '', start_date: '', end_date: '',
      registration_deadline: '', max_events_per_person: 3, description: '' })
  }
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (editId.value) {
      await meetApi.update(editId.value, form)
      ElMessage.success('更新成功')
    } else {
      await meetApi.create(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function setStatus(row, status) {
  try {
    await meetApi.setStatus(row.id, status)
    ElMessage.success('状态已更新')
    load()
  } catch {}
}

async function deleteMeet(row) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.name}」？`, '提示', { type: 'warning' })
    await meetApi.delete(row.id)
    ElMessage.success('已删除')
    load()
  } catch {}
}

onMounted(load)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
