<template>
  <div class="teacher-students">
    <!-- 主卡片 -->
    <el-card shadow="never">
      <template #header>
        <div class="page-header">
          <div class="page-title">
            <span>学生管理</span>
            <el-tag effect="dark" round size="small">{{ auth.user?.class_name }}</el-tag>
          </div>
          <div class="header-actions">
            <el-button plain size="small" @click="downloadTemplate">
              <el-icon><Download /></el-icon>下载模板
            </el-button>
            <el-upload :before-upload="handleImport" :show-file-list="false" accept=".xlsx,.xls">
              <el-button plain size="small" type="success">
                <el-icon><Upload /></el-icon>导入Excel
              </el-button>
            </el-upload>
            <el-button size="small" type="primary" @click="openDialog()">
              <el-icon><Plus /></el-icon>添加学生
            </el-button>
          </div>
        </div>
      </template>

      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input v-model="filterName" placeholder="搜索姓名或学号" clearable style="width:200px" size="small" @input="load">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="filterGender" clearable placeholder="性别筛选" style="width:100px" size="small" @change="load">
            <el-option label="全部" value="" /><el-option label="男生" value="male" /><el-option label="女生" value="female" />
          </el-select>
          <el-button size="small" text @click="clearFilter">清除筛选</el-button>
          <el-divider direction="vertical" />
          <el-popconfirm v-if="selectedIds.length" title="确认删除选中的学生？" @confirm="batchDelete">
            <template #reference>
              <el-button size="small" type="danger" plain>
                <el-icon><Delete /></el-icon>删除选中 ({{ selectedIds.length }})
              </el-button>
            </template>
          </el-popconfirm>
        </div>
        <div class="toolbar-right">
          <el-text size="small" type="info">共 <b>{{ total }}</b> 人</el-text>
        </div>
      </div>

      <!-- 表格 -->
      <el-table
        :data="students" v-loading="loading"
        @selection-change="onSelect"
        size="small" stripe
        :header-cell-style="{ background: '#fafafa', color: '#303133', fontWeight: 600 }"
        row-class-name="student-row"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column label="#" width="50" align="center">
          <template #default="{ $index }">
            <span class="row-num">{{ (page - 1) * pageSize + $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="student_id" label="学号" min-width="160" show-overflow-tooltip />
        <el-table-column prop="name" label="姓名" min-width="140" />
        <el-table-column label="性别" width="80" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.gender === 'male' ? 'primary' : 'danger'"
              effect="light" size="small" round
            >
              {{ row.gender === 'male' ? '♂ 男' : '♀ 女' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" :icon="Edit" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除此学生？" @confirm="deleteStudent(row)">
              <template #reference>
                <el-button link type="danger" size="small" :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-footer">
        <div class="page-size-select">
          <span>每页</span>
          <el-select v-model="pageSize" style="width:75px" size="small" @change="onPageSizeChange">
            <el-option v-for="n in [10,20,30,50,100]" :key="n" :label="n" :value="n" />
          </el-select>
          <span>条</span>
        </div>
        <el-pagination
          v-model:current-page="page" :page-size="pageSize" :total="total"
          layout="prev, pager, next" size="small" background @current-change="load"
        />
      </div>
    </el-card>

    <!-- 添加/编辑 -->
    <el-dialog v-model="dialogVisible" :title="editId ? '编辑学生' : '添加学生'" width="380px" :close-on-click-modal="false">
      <el-form :model="form" ref="formRef" label-width="70px">
        <el-form-item label="学号"><el-input v-model="form.student_id" placeholder="例如 20240001" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.name" placeholder="学生姓名" /></el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.gender">
            <el-radio-button label="male">男</el-radio-button>
            <el-radio-button label="female">女</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 导入结果 -->
    <el-dialog v-model="importResultVisible" title="导入结果" width="420px" align-center>
      <div style="text-align:center;padding:20px 0">
        <el-icon :size="48" :color="importResult.errors?.length ? '#f56c6c' : '#67c23a'">
          <SuccessFilled v-if="!importResult.errors?.length" /><WarningFilled v-else />
        </el-icon>
        <p style="margin-top:16px;font-size:15px;font-weight:600">{{ importResult.detail }}</p>
        <div v-if="importResult.created" style="margin-top:8px;color:#909399">
          新增 {{ importResult.created }} 人 · 更新 {{ importResult.updated }} 人
        </div>
        <div v-if="importResult.errors?.length" style="margin-top:12px;text-align:left">
          <el-tag v-for="e in importResult.errors" :key="e" type="danger" size="small" style="margin:2px;display:block">{{ e }}</el-tag>
        </div>
      </div>
      <template #footer><el-button type="primary" @click="importResultVisible = false; load()">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus, Edit, Delete, Download, Upload, SuccessFilled, WarningFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { studentApi, importApi } from '@/api'
import axios from 'axios'

const auth = useAuthStore()
const students = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const importResultVisible = ref(false)
const importResult = ref({})
const editId = ref(null)
const filterName = ref('')
const filterGender = ref('')
const selectedIds = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const form = reactive({ name: '', gender: 'male', student_id: '' })

function onSelect(rows) { selectedIds.value = rows.map(r => r.id) }
function clearFilter() { filterName.value = ''; filterGender.value = ''; load() }
function onPageSizeChange() { page.value = 1; load() }

async function batchDelete() {
  for (const id of selectedIds.value) await studentApi.delete(id)
  ElMessage.success(`已删除 ${selectedIds.value.length} 人`)
  selectedIds.value = []
  load()
}

async function load() {
  loading.value = true
  try {
    const params = { class_name: auth.user.class_name, page: page.value, page_size: pageSize.value }
    if (filterName.value) params.name = filterName.value
    if (filterGender.value) params.gender = filterGender.value
    const res = await studentApi.list(params)
    students.value = res.results || res
    total.value = res.count || 0
  } catch { total.value = 0 }
  loading.value = false
}

function openDialog(row) {
  editId.value = row?.id || null
  if (row) Object.assign(form, row)
  else Object.assign(form, { name: '', gender: 'male', student_id: '' })
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    const data = { ...form, class_name: auth.user.class_name }
    if (editId.value) { await studentApi.update(editId.value, data); ElMessage.success('已更新') }
    else { await studentApi.create(data); ElMessage.success('已添加') }
    dialogVisible.value = false
    load()
  } finally { saving.value = false }
}

async function deleteStudent(row) {
  await studentApi.delete(row.id)
  ElMessage.success('已删除')
  load()
}

async function handleImport(file) {
  const formData = new FormData(); formData.append('file', file)
  const res = await importApi.importExcel(formData)
  importResult.value = res
  importResultVisible.value = true
  return false
}

async function downloadTemplate() {
  const token = localStorage.getItem('access_token')
  const res = await axios.get('/api/students/export_template/', {
    headers: { Authorization: `Bearer ${token}` }, responseType: 'blob'
  })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([res.data]))
  link.download = '学生导入模板.xlsx'
  link.click()
}

onMounted(load)
</script>

<style scoped>
.teacher-students {
  display: flex; flex-direction: column;
}

/* Header */
.page-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
.page-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; }
.header-actions { display: flex; gap: 8px; }

/* Toolbar */
.toolbar {
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 10px; margin-bottom: 12px; padding: 10px 14px;
  background: #fafbfc; border-radius: 8px;
}
.toolbar-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.toolbar-right { flex-shrink: 0; }

/* Table */
.row-num { color: #909399; font-size: 12px; }

/* Pagination */
.pagination-footer {
  display: flex; justify-content: flex-end; align-items: center;
  gap: 12px; padding-top: 10px;
  border-top: 1px solid #f0f0f0; margin-top: 8px;
}
.page-size-select { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #909399; }
</style>

<style>
.teacher-students {
  height: calc(100vh - 64px);
  display: flex; flex-direction: column;
}
.teacher-students > .el-row { flex-shrink: 0; }
.teacher-students > .el-card {
  flex: 1; display: flex; flex-direction: column; min-height: 0;
}
.teacher-students > .el-card > .el-card__body {
  flex: 1; display: flex; flex-direction: column; overflow: hidden;
}
.teacher-students .el-table {
  flex: 1; font-size: 14px;
}
.teacher-students .el-table__body-wrapper {
  overflow-y: auto;
}
.teacher-students .el-table th { font-size: 14px; }
.teacher-students .el-table td { font-size: 14px; padding: 10px 0; }
</style>
