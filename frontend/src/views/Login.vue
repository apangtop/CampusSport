<template>
  <div class="login-page">
    <div class="login-box">
      <div class="login-header">
        <div class="logo">🏃</div>
        <h1>CampusSport</h1>
        <p>校园运动会管理系统</p>
      </div>
      <el-form :model="form" :rules="rules" ref="formRef" size="large" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="请输入账号" :prefix-icon="User" clearable />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码"
            :prefix-icon="Lock" show-password clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-footer">
        <el-tag type="info" size="small">体育老师 / 班主任 / 裁判 统一入口</el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  await formRef.value.validate()
  loading.value = true
  try {
    const user = await auth.login(form.username, form.password)
    ElMessage.success(`欢迎，${user.real_name || user.username}！`)
    const redirectMap = { admin: '/admin', teacher: '/teacher', referee: '/referee' }
    router.push(redirectMap[user.role] || '/login')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a6db5 0%, #0d4a8a 50%, #072d5c 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}
.login-box {
  background: #fff;
  border-radius: 16px;
  padding: 48px 40px;
  width: 420px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}
.login-header {
  text-align: center;
  margin-bottom: 36px;
}
.logo { font-size: 52px; margin-bottom: 8px; }
.login-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #1a6db5;
  margin: 0 0 6px;
}
.login-header p { color: #888; font-size: 14px; margin: 0; }
.login-btn { width: 100%; height: 48px; font-size: 16px; letter-spacing: 4px; }
.login-footer { text-align: center; margin-top: 16px; }
</style>
