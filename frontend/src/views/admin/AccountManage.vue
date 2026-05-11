<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">账号管理</span>
          <el-button type="primary" :icon="Plus" @click="openDialog()">新建账号</el-button>
        </div>
      </template>
      <el-tabs v-model="activeTab" @tab-change="load">
        <el-tab-pane label="班主任" name="teacher" />
        <el-tab-pane label="裁判" name="referee" />
        <el-tab-pane label="体育老师" name="admin" />
      </el-tabs>
      <el-table :data="users" v-loading="loading">
        <el-table-column prop="username" label="账号" width="130" />
        <el-table-column prop="real_name" label="姓名" width="100" />
        <el-table-column prop="class_name" label="班级/负责项目" min-width="140" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="is_active" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="warning" @click="resetPwd(row)">重置密码</el-button>
            <el-button link :type="row.is_active ? 'danger' : 'success'" @click="toggleActive(row)">
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑账号' : '新建账号'" width="480px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" :disabled="!!editId" />
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="!editId">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="form.real_name" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width:100%">
            <el-option label="班主任" value="teacher" />
            <el-option label="裁判" value="referee" />
            <el-option label="体育老师" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级" v-if="form.role === 'teacher'">
          <ClassSelector v-model="form.class_name" :clearable="false" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" />
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
import { userApi } from '@/api'
import ClassSelector from '@/components/ClassSelector.vue'

const users = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editId = ref(null)
const formRef = ref()
const activeTab = ref('teacher')

const defaultForm = () => ({ username: '', password: '', real_name: '', role: 'teacher', class_name: '', phone: '' })
const form = reactive(defaultForm())
const rules = {
  username: [{ required: true, message: '请输入账号' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入姓名' }]
}

async function load() {
  loading.value = true
  const res = await userApi.list({ role: activeTab.value })
  users.value = res.results || res
  loading.value = false
}

function openDialog(row) {
  editId.value = row?.id || null
  if (row) {
    Object.assign(form, { username: row.username, real_name: row.real_name, role: row.role, class_name: row.class_name || '', phone: row.phone || '', password: '' })
  } else {
    Object.assign(form, defaultForm())
    form.role = activeTab.value
  }
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (editId.value) {
      await userApi.update(editId.value, { real_name: form.real_name, class_name: form.class_name, phone: form.phone })
    } else {
      await userApi.create(form)
    }
    ElMessage.success(editId.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function resetPwd(row) {
  await ElMessageBox.prompt('请输入新密码', '重置密码', { inputType: 'password', inputValue: '123456' })
    .then(async ({ value }) => {
      await userApi.resetPassword(row.id, { new_password: value })
      ElMessage.success('密码已重置')
    }).catch(() => {})
}

async function toggleActive(row) {
  await userApi.update(row.id, { is_active: !row.is_active })
  ElMessage.success(row.is_active ? '已禁用' : '已启用')
  load()
}

onMounted(load)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
