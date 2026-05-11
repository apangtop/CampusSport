import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true }
  },
  // 体育老师（admin）路由
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { role: 'admin' },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', name: 'AdminDashboard', component: () => import('@/views/admin/Dashboard.vue') },
      { path: 'meets', name: 'MeetList', component: () => import('@/views/admin/MeetList.vue') },
      { path: 'meets/:id', name: 'MeetDetail', component: () => import('@/views/admin/MeetDetail.vue') },
      { path: 'meets/:id/events', name: 'EventManage', component: () => import('@/views/admin/EventManage.vue') },
      { path: 'meets/:id/registration', name: 'RegistrationManage', component: () => import('@/views/admin/RegistrationManage.vue') },
      { path: 'meets/:id/schedule', name: 'ScheduleManage', component: () => import('@/views/admin/ScheduleManage.vue') },
      { path: 'meets/:id/scores', name: 'ScoreManage', component: () => import('@/views/admin/ScoreManage.vue') },
      { path: 'meets/:id/points', name: 'PointsBoard', component: () => import('@/views/admin/PointsBoard.vue') },
      { path: 'meets/:id/report', name: 'ReportExport', component: () => import('@/views/admin/ReportExport.vue') },
      { path: 'meets/:id/participants', name: 'ParticipantView', component: () => import('@/views/admin/ParticipantView.vue') },
      { path: 'accounts', name: 'AccountManage', component: () => import('@/views/admin/AccountManage.vue') },
      { path: 'students', name: 'StudentManage', component: () => import('@/views/admin/StudentManage.vue') },
      { path: 'history', name: 'HistoryData', component: () => import('@/views/admin/HistoryData.vue') },
    { path: 'change-password', name: 'AdminChangePassword', component: () => import('@/views/ChangePassword.vue') },
    ]
  },
  // 班主任（teacher）路由
  {
    path: '/teacher',
    component: () => import('@/layouts/TeacherLayout.vue'),
    meta: { role: 'teacher' },
    children: [
      { path: '', redirect: '/teacher/dashboard' },
      { path: 'dashboard', name: 'TeacherDashboard', component: () => import('@/views/teacher/Dashboard.vue') },
      { path: 'events', name: 'TeacherEvents', component: () => import('@/views/teacher/EventList.vue') },
      { path: 'students', name: 'TeacherStudents', component: () => import('@/views/teacher/Students.vue') },
      { path: 'register', name: 'TeacherRegister', component: () => import('@/views/teacher/Register.vue') },
      { path: 'my-registrations', name: 'MyRegistrations', component: () => import('@/views/teacher/MyRegistrations.vue') },
      { path: 'scores', name: 'TeacherScores', component: () => import('@/views/teacher/Scores.vue') },
      { path: 'points', name: 'TeacherPoints', component: () => import('@/views/teacher/Points.vue') },
    { path: 'change-password', name: 'TeacherChangePassword', component: () => import('@/views/ChangePassword.vue') },
    ]
  },
  // 裁判（referee）路由
  {
    path: '/referee',
    component: () => import('@/layouts/RefereeLayout.vue'),
    meta: { role: 'referee' },
    children: [
      { path: '', redirect: '/referee/dashboard' },
      { path: 'dashboard', name: 'RefereeDashboard', component: () => import('@/views/referee/Dashboard.vue') },
      { path: 'my-events', name: 'MyEvents', component: () => import('@/views/referee/MyEvents.vue') },
      { path: 'score-entry', name: 'ScoreEntry', component: () => import('@/views/referee/ScoreEntry.vue') },
      { path: 'points', name: 'RefereePoints', component: () => import('@/views/referee/Points.vue') },
      { path: 'confrontation', name: 'ConfrontationEntry', component: () => import('@/views/referee/ConfrontationEntry.vue') },
    { path: 'change-password', name: 'RefereeChangePassword', component: () => import('@/views/ChangePassword.vue') },
    ]
  },
  { path: '/', redirect: '/login' },
  { path: '/:pathMatch(.*)*', redirect: '/login' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.guest) return next()
  if (!auth.isLoggedIn) return next('/login')
  if (to.meta.role && auth.role !== to.meta.role) {
    const redirectMap = { admin: '/admin', teacher: '/teacher', referee: '/referee' }
    return next(redirectMap[auth.role] || '/login')
  }
  next()
})

export default router
