<template>
  <div>
    <el-card shadow="never" style="max-width:500px">
      <template #header>
        <span style="font-size:16px;font-weight:600">修改密码</span>
      </template>
      <el-form :model="form" label-width="90px" ref="formRef" :rules="rules">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="form.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="submit">确认修改</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { userApi } from '@/api'

const auth = useAuthStore()
const formRef = ref()
const submitting = ref(false)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirm = (rule, value, callback) => {
  if (value !== form.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' }
  ]
}

async function submit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await userApi.changePassword(auth.user.id, {
      old_password: form.old_password,
      new_password: form.new_password
    })
    ElMessage.success('密码修改成功')
    form.old_password = ''
    form.new_password = ''
    form.confirm_password = ''
  } finally {
    submitting.value = false
  }
}
</script>
