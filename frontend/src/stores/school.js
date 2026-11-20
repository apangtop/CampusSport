import { defineStore } from 'pinia'
import axios from 'axios'
import request from '@/api/request'
import { gradeForClass } from '@/utils/schoolDirectory'

let directoryRequest = null
let directoryOwner = null
export const useSchoolStore = defineStore('school', {
  state: () => ({ school_name: '', system_name: 'CampusSport', classes: [], grades: [] }),
  actions: {
    gradeForClass(name) { return gradeForClass(this.classes, name) },
    isGrade(value) { return this.grades.includes(value) || /^\d{4}级$/.test(value) },
    async loadBranding() {
      // Public login branding must not send a stale JWT or trigger the login interceptor.
      const { data } = await axios.get('/api/school/branding/', { timeout: 15000 })
      this.school_name = data.school_name
      this.system_name = data.system_name
      document.title = this.school_name ? `${this.school_name} · ${this.system_name}` : this.system_name
    },
    async loadDirectory() {
      const owner = localStorage.getItem('access_token')
      if (!directoryRequest || owner !== directoryOwner) {
        directoryOwner = owner
        const pending = request.get('/school/directory/')
        directoryRequest = pending
        pending.finally(() => { if (directoryRequest === pending) directoryRequest = null }).catch(() => {})
      }
      const result = await directoryRequest
      if (owner !== localStorage.getItem('access_token')) return
      this.classes = result.classes
      this.grades = result.grades
    }
  }
})
