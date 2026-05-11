<template>
  <el-container class="app-layout">
    <div v-if="isMobile && !collapsed" class="mobile-overlay" @click="collapsed = true" />
    <el-aside :width="collapsed ? '0px' : '220px'" class="sidebar">
      <div class="logo-area" @click="collapsed = !collapsed">
        <span class="logo-icon">🏃</span>
        <span class="logo-text">CampusSport</span>
      </div>
      <el-menu :router="true" :default-active="$route.path" background-color="#001529"
        text-color="#ffffffa6" active-text-color="#fff">
        <el-menu-item index="/teacher/dashboard"><el-icon><HomeFilled /></el-icon><template #title>首页</template></el-menu-item>
        <el-menu-item index="/teacher/events"><el-icon><List /></el-icon><template #title>项目浏览</template></el-menu-item>
        <el-menu-item index="/teacher/students"><el-icon><Avatar /></el-icon><template #title>学生管理</template></el-menu-item>
        <el-menu-item index="/teacher/register"><el-icon><EditPen /></el-icon><template #title>报名管理</template></el-menu-item>
        <el-menu-item index="/teacher/my-registrations"><el-icon><Document /></el-icon><template #title>本班报名情况</template></el-menu-item>
        <el-menu-item index="/teacher/scores"><el-icon><DataLine /></el-icon><template #title>成绩查看</template></el-menu-item>
        <el-menu-item index="/teacher/points"><el-icon><Trophy /></el-icon><template #title>积分榜</template></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <el-icon v-if="isMobile" class="menu-toggle" :size="22" @click="collapsed = !collapsed">
            <Expand v-if="collapsed" /><Fold v-else />
          </el-icon>
          <span class="header-title" v-if="isMobile && collapsed">CampusSport</span>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="30" style="background:#67c23a">{{ auth.user?.real_name?.charAt(0) || 'T' }}</el-avatar>
              <span class="user-name">{{ auth.user?.real_name || auth.user?.username }}</span>
              <el-tag v-if="!isMobile" size="small" type="success">班主任</el-tag>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="changePassword">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="app-main"><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { Expand, Fold } from '@element-plus/icons-vue'

const auth = useAuthStore()
const router = useRouter()
const collapsed = ref(window.innerWidth < 768)
const isMobile = ref(window.innerWidth < 768)

function onResize() {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) collapsed.value = true
  else collapsed.value = false
}
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

function handleCommand(cmd) {
  if (cmd === 'changePassword') { router.push('/teacher/change-password'); if (isMobile.value) collapsed.value = true }
  else if (cmd === 'logout') {
    ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' }).then(() => { auth.logout(); router.push('/login') }).catch(() => {})
  }
}
</script>

<style scoped>
.app-layout { height: 100vh; }
.sidebar { background: #001529; transition: width 0.2s; overflow: hidden; z-index: 100; }
.mobile-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 99; }
.logo-area { height: 64px; display: flex; align-items: center; justify-content: center; cursor: pointer; border-bottom: 1px solid #ffffff15; gap: 10px; }
.logo-icon { font-size: 28px; }
.logo-text { color: #fff; font-size: 18px; font-weight: 700; white-space: nowrap; }
.el-menu { border-right: none; }
.app-header { background: #fff; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #f0f0f0; padding: 0 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); height: 56px; }
.menu-toggle { cursor: pointer; color: #333; margin-right: 10px; }
.header-title { font-weight: 600; font-size: 15px; }
.user-info { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.app-main { background: #f5f7fa; padding: 12px; overflow-y: auto; }
@media (min-width: 768px) { .app-header { padding: 0 24px; height: 60px; } .app-main { padding: 20px; } }
@media (max-width: 767px) { .sidebar { position: fixed; left: 0; top: 0; bottom: 0; } .user-name { display: none; } }
</style>
