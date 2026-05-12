<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">学生管理</span>
          <div style="display:flex;gap:8px;align-items:center">
            <el-button @click="downloadTemplate">下载导入模板</el-button>
            <ClassSelector v-model="importClass" :clearable="true" year-width="120px" class-width="90px" style="margin-right:4px" />
            <el-upload :before-upload="handleImport" :show-file-list="false" accept=".xlsx,.xls">
              <el-button type="success">
                <el-icon><Upload /></el-icon> Excel批量导入
              </el-button>
            </el-upload>
            <el-button type="primary" :icon="Plus" @click="openDialog()">手动添加</el-button>
          </div>
        </div>
      </template>

      <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">
        <el-input v-model="filterName" placeholder="搜索姓名" clearable style="width:160px" @input="onFilterChange" />
        <ClassSelector v-model="filterClass" @change="onFilterChange" :clearable="true" :year-filter="true" />
        <el-select v-model="filterGender" clearable placeholder="性别" style="width:90px" @change="onFilterChange">
          <el-option label="男" value="male" />
          <el-option label="女" value="female" />
        </el-select>
        <el-button @click="clearFilter">重置</el-button>
        <el-button v-if="selectedIds.length" type="danger" @click="batchDelete">删除选中（{{ selectedIds.length }}）</el-button>
      </div>

      <el-table :data="students" v-loading="loading" @selection-change="onSelect">
        <el-table-column type="selection" width="45" />
        <el-table-column label="序号" width="55" align="center">
          <template #default="{ $index }">{{ (page - 1) * pageSize + $index + 1 }}</template>
        </el-table-column>
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="gender" label="性别" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.gender === 'male' ? 'primary' : 'danger'" size="small">
              {{ row.gender === 'male' ? '男' : '女' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" width="130" />
        <el-table-column prop="grade" label="年级" width="100" />
        <el-table-column prop="student_id" label="学号" min-width="120" />
        <el-table-column label="操作" width="130" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="deleteStudent(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="display:flex;justify-content:flex-end;align-items:center;margin-top:16px;gap:8px">
        <span style="font-size:13px;color:#909399">每页</span>
        <el-select v-model="pageSize" style="width:70px" @change="load" size="small">
          <el-option label="10" :value="10" /><el-option label="20" :value="20" /><el-option label="30" :value="30" /><el-option label="50" :value="50" /><el-option label="100" :value="100" />
        </el-select>
        <span style="font-size:13px;color:#909399">条</span>
        <el-pagination v-model:current-page="page" :page-size="pageSize"
          :total="total" layout="prev, pager, next" @current-change="load" size="small" background />
      </div>
    </el-card>

    <!-- 导入结果提示 -->
    <el-dialog v-model="importResultVisible" title="导入结果" width="400px">
      <el-result :icon="importResult.errors?.length ? 'warning' : 'success'"
        :title="importResult.detail">
        <template #extra>
          <div v-if="importResult.errors?.length">
            <p style="color:#f56c6c" v-for="e in importResult.errors" :key="e">{{ e }}</p>
          </div>
        </template>
      </el-result>
      <template #footer>
        <el-button type="primary" @click="importResultVisible = false; load()">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editId ? '编辑学生' : '添加学生'" width="420px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-radio-group v-model="form.gender">
            <el-radio label="male">男</el-radio>
            <el-radio label="female">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="班级" prop="class_name">
          <ClassSelector v-model="form.class_name" :clearable="false" />
        </el-form-item>
        <el-form-item label="学号">
          <el-input v-model="form.student_id" placeholder="可选" />
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
import { Plus, Upload } from '@element-plus/icons-vue'
import { studentApi, importApi } from '@/api'
import axios from 'axios'
import ClassSelector from '@/components/ClassSelector.vue'

const students = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const importResultVisible = ref(false)
const importResult = ref({})
const editId = ref(null)
const formRef = ref()
const filterName = ref('')
const filterClass = ref('')
const filterGender = ref('')
const selectedIds = ref([])
const page = ref(1)

function onSelect(rows) { selectedIds.value = rows.map(r => r.id) }

async function batchDelete() {
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 名学生？`, '批量删除', { type: 'warning' })
    for (const id of selectedIds.value) {
      await studentApi.delete(id)
    }
    ElMessage.success(`已删除 ${selectedIds.value.length} 名学生`)
    selectedIds.value = []
    load()
  } catch {}
}
const pageSize = ref(20)
const total = ref(0)

const defaultForm = () => ({ name: '', gender: 'male', class_name: '', student_id: '' })

function clearFilter() {
  filterName.value = ''
  filterClass.value = ''
  filterGender.value = ''
  load()
}
const form = reactive(defaultForm())
const rules = {
  name: [{ required: true, message: '请输入姓名' }],
  gender: [{ required: true }],
  class_name: [{ required: true, message: '请输入班级' }]
}

function onFilterChange() {
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  const params = { page: page.value, page_size: pageSize.value }
  if (filterName.value) params.name = filterName.value
  if (filterClass.value) params.class_name = filterClass.value
  if (filterGender.value) params.gender = filterGender.value
  const res = await studentApi.list(params)
  students.value = res.results || res
  total.value = res.count || students.value.length
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
    // 从班级名称提取年级（统一为 "2028级" 格式，与种子数据一致）
    const match = form.class_name?.match(/^(\d{4})级/)
    const grade = match ? `${match[1]}级` : ''
    const data = { ...form, grade }
    if (editId.value) {
      await studentApi.update(editId.value, data)
      ElMessage.success('更新成功')
    } else {
      await studentApi.create(data)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function deleteStudent(row) {
  await ElMessageBox.confirm(`确认删除学生「${row.name}」？`, '提示', { type: 'warning' })
  await studentApi.delete(row.id)
  ElMessage.success('已删除')
  load()
}

const importClass = ref('')

async function handleImport(file) {
  const formData = new FormData()
  formData.append('file', file)
  if (importClass.value) formData.append('class_name', importClass.value)
  const res = await importApi.importExcel(formData)
  importResult.value = res
  importResultVisible.value = true
  return false
}

async function downloadTemplate() {
  const token = localStorage.getItem('access_token')
  const res = await axios.get('/api/students/export_template/', {
    headers: { Authorization: `Bearer ${token}` },
    responseType: 'blob'
  })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([res.data]))
  link.download = '学生导入模板.xlsx'
  link.click()
}

onMounted(load)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
