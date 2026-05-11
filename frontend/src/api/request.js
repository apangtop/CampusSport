import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000
})

request.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  res => {
    // blob 响应直接返回完整 response，供下载使用
    if (res.config.responseType === 'blob') return res
    return res.data
  },
  err => {
    const status = err.response?.status
    const msg = err.response?.data?.detail || err.response?.data?.message || '请求失败'
    if (status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_info')
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else if (status === 403) {
      ElMessage.error('无权限执行此操作')
    } else {
      ElMessage.error(msg)
    }
    return Promise.reject(err)
  }
)

export default request
