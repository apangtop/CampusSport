<template>
  <el-container class="app-layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar">
      <div class="logo-area" @click="collapsed = !collapsed">
        <span class="logo-icon">🏃</span>
        <span v-if="!collapsed" class="logo-text">CampusSport</span>
      </div>
      <el-menu :router="true" :default-active="$route.path" background-color="#001529"
        text-color="#ffffffa6" active-text-color="#fff" :collapse="collapsed">
        <el-menu-item index="/referee/dashboard">
          <el-icon><HomeFilled /></el-icon><template #title>我的项目</template>
        </el-menu-item>
        <el-menu-item index="/referee/score-entry">
          <el-icon><EditPen /></el-icon><template #title>成绩录入</template>
        </el-menu-item>
        <el-menu-item index="/referee/confrontation">
          <el-icon><Fist /></el-icon><template #title>拔河录入</template>
        </el-menu-item>
        <el-menu-item index="/referee/points">
          <el-icon><Trophy /></el-icon><template #title>积分榜</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <div class="header-left"></div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" style="background:#e6a23c">
                {{ auth.user?.real_name?.charAt(0) || 'R' }}
              </el-avatar>
              <span>{{ auth.user?.real_name || auth.user?.username }}</span>
              <el-tag size="small" type="warning">裁判</el-tag>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="changePassword">修改密码</el-dropdown-item><el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const collapsed = ref(false)

function handleCommand(cmd) {
  if (cmd === 'changePassword') {
    router.push('/referee/change-password')
  } else if (cmd === 'logout') {
    ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' }).then(() => {
      auth.logout()
      router.push('/login')
    }).catch(() => {})
  }
}
</script>

<style scoped>
.app-layout { height: 100vh; }
.sidebar { background: #001529; transition: width 0.2s; overflow: hidden; }
.logo-area {
  height: 64px; display: flex; align-items: center; justify-content: center;
  cursor: pointer; border-bottom: 1px solid #ffffff15; gap: 10px;
}
.logo-icon { font-size: 28px; }
.logo-text { color: #fff; font-size: 18px; font-weight: 700; white-space: nowrap; }
.el-menu { border-right: none; }
.app-header {
  background: #fff; display: flex; align-items: center;
  justify-content: space-between; border-bottom: 1px solid #f0f0f0;
  padding: 0 24px; box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
.user-info { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.app-main { background: #f5f7fa; padding: 20px; overflow-y: auto; }
</style>
