import request from './request'

// ===== 认证 =====
export const authApi = {
  login: data => request.post('/auth/login/', data),
  refresh: data => request.post('/auth/refresh/', data),
  getMe: () => request.get('/users/me/')
}

// ===== 用户管理 =====
export const userApi = {
  list: params => request.get('/users/', { params }),
  create: data => request.post('/users/', data),
  update: (id, data) => request.patch(`/users/${id}/`, data),
  delete: id => request.delete(`/users/${id}/`),
  resetPassword: (id, data) => request.post(`/users/${id}/reset_password/`, data),
  changePassword: (id, data) => request.post(`/users/${id}/change_password/`, data)
}

// ===== 运动会 =====
export const meetApi = {
  list: params => request.get('/sports-meets/', { params }),
  get: id => request.get(`/sports-meets/${id}/`),
  create: data => request.post('/sports-meets/', data),
  update: (id, data) => request.patch(`/sports-meets/${id}/`, data),
  delete: id => request.delete(`/sports-meets/${id}/`),
  setStatus: (id, status) => request.post(`/sports-meets/${id}/set_status/`, { status }),
  scheduleOverview: id => request.get(`/sports-meets/${id}/schedule_overview/`),
  scoreSummary: (id, params) => request.get(`/sports-meets/${id}/score_summary/`, { params })
}

// ===== 比赛项目 =====
export const eventApi = {
  list: params => request.get('/events/', { params }),
  get: id => request.get(`/events/${id}/`),
  create: data => request.post('/events/', data),
  update: (id, data) => request.patch(`/events/${id}/`, data),
  delete: id => request.delete(`/events/${id}/`),
  participants: id => request.get(`/events/${id}/participants/`),
  autoAssignLanes: (id, data) => request.post(`/events/${id}/auto_assign_lanes/`, data)
}

// ===== 赛程 =====
export const scheduleApi = {
  list: params => request.get('/schedules/', { params }),
  create: data => request.post('/schedules/', data),
  update: (id, data) => request.patch(`/schedules/${id}/`, data),
  delete: id => request.delete(`/schedules/${id}/`)
}

// ===== 学生 =====
export const studentApi = {
  list: params => request.get('/students/', { params }),
  create: data => request.post('/students/', data),
  update: (id, data) => request.patch(`/students/${id}/`, data),
  delete: id => request.delete(`/students/${id}/`),
  bulkCreate: data => request.post('/students/bulk/', data)
}

// ===== 报名 =====
export const registrationApi = {
  list: params => request.get('/registrations/', { params }),
  create: data => request.post('/registrations/', data),
  update: (id, data) => request.patch(`/registrations/${id}/`, data),
  delete: id => request.delete(`/registrations/${id}/`),
  bulkRegister: data => request.post('/registrations/bulk_register/', data),
  approve: id => request.post(`/registrations/${id}/approve/`),
  reject: id => request.post(`/registrations/${id}/reject/`),
  cancel: id => request.post(`/registrations/${id}/cancel/`),
  approveAll: data => request.post('/registrations/approve_all/', data)
}

// ===== 团体报名 =====
export const teamRegistrationApi = {
  list: params => request.get('/team-registrations/', { params }),
  create: data => request.post('/team-registrations/', data),
  update: (id, data) => request.patch(`/team-registrations/${id}/`, data),
  delete: id => request.delete(`/team-registrations/${id}/`),
  cancel: id => request.post(`/team-registrations/${id}/cancel/`)
}

// ===== 成绩 =====
export const scoreApi = {
  list: params => request.get('/scores/', { params }),
  create: data => request.post('/scores/', data),
  update: (id, data) => request.patch(`/scores/${id}/`, data),
  batchSubmit: data => request.post('/scores/batch_submit/', data),
  calculateRanks: data => request.post('/scores/calculate_ranks/', data),
  confirmAdvancement: data => request.post('/scores/confirm_advancement/', data),
  autoAdvanceTop: data => request.post('/scores/auto_advance_top/', data)
}

// ===== 团体成绩 =====
export const teamScoreApi = {
  list: params => request.get('/team-scores/', { params }),
  create: data => request.post('/team-scores/', data),
  update: (id, data) => request.patch(`/team-scores/${id}/`, data)
}

// ===== 积分榜 =====
export const pointsApi = {
  list: params => request.get('/class-points/', { params }),
  recalculate: data => request.post('/class-points/recalculate/', data)
}

// ===== 历届数据 =====
export const historyApi = {
  meets: () => request.get('/history/meets/'),
  points: params => request.get('/history/points/', { params }),
  eventBest: params => request.get('/history/event-best/', { params }),
  student: params => request.get('/history/student/', { params })
}

// ===== 学生导入 =====
export const importApi = {
  importExcel: (formData) => request.post('/students/import_excel/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  downloadTemplate: () => request.get('/students/export_template/', { responseType: 'blob' })
}

// ===== 报告导出 =====
export const reportApi = {
  downloadOrderBook: (meetId) => {
    return request.get('/reports/generate_order_book/', {
      params: { sports_meet_id: meetId },
      responseType: 'blob'
    })
  },
  downloadResultReport: (meetId) => {
    return request.get('/reports/generate_result_report/', {
      params: { sports_meet_id: meetId },
      responseType: 'blob'
    })
  }
}
