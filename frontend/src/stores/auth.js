import { defineStore } from 'pinia'
import { authApi } from '@/api'
import { useSchoolStore } from '@/stores/school'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    user: JSON.parse(localStorage.getItem('user_info') || 'null')
  }),
  getters: {
    isLoggedIn: state => !!state.token,
    isAdmin: state => state.user?.role === 'admin',
    isTeacher: state => state.user?.role === 'teacher',
    isReferee: state => state.user?.role === 'referee',
    role: state => state.user?.role || ''
  },
  actions: {
    async login(username, password) {
      const res = await authApi.login({ username, password })
      useSchoolStore().classes = []
      useSchoolStore().grades = []
      this.token = res.access
      this.user = res.user
      localStorage.setItem('access_token', res.access)
      localStorage.setItem('user_info', JSON.stringify(res.user))
      return res.user
    },
    logout() {
      useSchoolStore().classes = []
      useSchoolStore().grades = []
      this.token = ''
      this.user = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_info')
    }
  }
})
