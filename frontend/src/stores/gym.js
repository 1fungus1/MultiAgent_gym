import { defineStore } from 'pinia'
import { adminApi, memberApi } from '@/api/gym'

function pad(value) {
  return String(value).padStart(2, '0')
}

function formatDateTime(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function normalizeDateTime(value) {
  if (!value) return value
  if (value instanceof Date) return formatDateTime(value)
  if (typeof value === 'string') {
    const trimmedValue = value.trim()
    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(trimmedValue)) return trimmedValue
    const isoMatch = trimmedValue.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/)
    if (isoMatch) return `${isoMatch[1]} ${isoMatch[2]}`
    const date = new Date(trimmedValue)
    if (!Number.isNaN(date.getTime())) return formatDateTime(date)
  }
  return value
}

export const useGymStore = defineStore('gym', {
  state: () => ({
    members: [],
    memberTotal: 0,
    memberPageNum: 1,
    memberPageSize: 10,
    memberKeyword: '',
    coaches: [],
    coachTotal: 0,
    coachPageNum: 1,
    coachPageSize: 10,
    coachKeyword: '',
    courses: [],
    courseTotal: 0,
    coursePageNum: 1,
    coursePageSize: 10,
    courseKeyword: '',
    appointments: [],
    currentMemberId: null,
  }),
  getters: {
    dashboard: (state) => ({
      memberCount: state.memberTotal || state.members.length,
      coachCount: state.coachTotal || state.coaches.filter((item) => item.status === 1).length,
      courseCount: state.courses.length,
      appointmentCount: state.appointments.filter((item) => item.status === 'reserved').length,
    }),
    courseRows: (state) =>
      state.courses.map((course) => ({
        ...course,
        coachName: course.coachName || state.coaches.find((coach) => coach.id === course.coachId)?.name || '-',
      })),
    appointmentRows: (state) =>
      state.appointments.map((appointment) => {
        const member = state.members.find((item) => item.id === appointment.memberId)
        const course = state.courses.find((item) => item.id === appointment.courseId)
        const coach = state.coaches.find((item) => item.id === course?.coachId)
        return {
          ...appointment,
          memberName: appointment.memberName || member?.name || '-',
          courseName: appointment.courseName || course?.name || '-',
          courseTime: appointment.courseTime || course?.startTime || '-',
          coachName: appointment.coachName || coach?.name || '-',
        }
      }),
    currentMember: (state) => state.members.find((item) => item.id === state.currentMemberId),
    myAppointments() {
      return this.appointmentRows.filter((item) => item.memberId === this.currentMemberId)
    },
  },
  actions: {
    async loadAdminData() {
      const [dashboard, coaches, courses, appointments] = await Promise.all([
        adminApi.dashboard(),
        adminApi.coaches(),
        adminApi.courses(),
        adminApi.appointments(),
      ])
      this.members = []
      this.coaches = coaches || []
      this.courses = courses || []
      this.appointments = appointments || []
      if (dashboard) {
        this.memberTotal = dashboard.memberCount || 0
        this.coachTotal = dashboard.coachCount || 0
        this.courseTotal = dashboard.courseCount || 0
        this.coursePageNum = 1
        this.coursePageSize = 10
      }
    },
    async loadMemberPage(params = {}) {
      const pageNum = params.pageNum || this.memberPageNum || 1
      const pageSize = params.pageSize || this.memberPageSize || 10
      const keyword = typeof params.keyword === 'string' ? params.keyword : this.memberKeyword || ''
      const result = await adminApi.memberPage({ pageNum, pageSize, keyword })
      this.members = result?.records || []
      this.memberTotal = result?.total || 0
      this.memberPageNum = result?.pageNum || pageNum
      this.memberPageSize = result?.pageSize || pageSize
      this.memberKeyword = keyword
    },
    async loadCoaches() {
      this.coaches = (await adminApi.coaches()) || []
    },
    async fetchCoaches() {
      await this.loadCoaches()
    },
    async loadCoachPage(params = {}) {
      const pageNum = params.pageNum || this.coachPageNum || 1
      const pageSize = params.pageSize || this.coachPageSize || 10
      const keyword = typeof params.keyword === 'string' ? params.keyword : this.coachKeyword || ''
      const result = await adminApi.coachPage({ pageNum, pageSize, keyword })
      this.coaches = result?.records || []
      this.coachTotal = result?.total || 0
      this.coachPageNum = result?.pageNum || pageNum
      this.coachPageSize = result?.pageSize || pageSize
      this.coachKeyword = keyword
    },
    async loadCoursePage(params = {}) {
      const pageNum = params.pageNum || this.coursePageNum || 1
      const pageSize = params.pageSize || this.coursePageSize || 10
      const keyword = typeof params.keyword === 'string' ? params.keyword : this.courseKeyword || ''
      const result = await adminApi.coursePage({ pageNum, pageSize, keyword })
      this.courses = result?.records || []
      this.courseTotal = result?.total || 0
      this.coursePageNum = result?.pageNum || pageNum
      this.coursePageSize = result?.pageSize || pageSize
      this.courseKeyword = keyword
    },
    async loadMemberData() {
      const [profile, courses, appointments] = await Promise.all([
        memberApi.profile(),
        memberApi.courses(),
        memberApi.appointments(),
      ])
      if (profile) {
        this.currentMemberId = profile.id
        const index = this.members.findIndex((item) => item.id === profile.id)
        if (index >= 0) this.members[index] = profile
        else this.members = [profile, ...this.members]
      }
      this.courses = courses || []
      this.appointments = appointments || []
    },
    async saveMember(payload) {
      const { username, password, ...member } = payload
      const request = { member, username, password }
      if (payload.id) await adminApi.updateMember(payload.id, request)
      else await adminApi.createMember(request)
      await this.loadMemberPage()
    },
    async removeMember(id) {
      await adminApi.deleteMember(id)
      const total = Math.max(this.memberTotal - 1, 0)
      const pages = Math.max(Math.ceil(total / this.memberPageSize), 1)
      await this.loadMemberPage({ pageNum: Math.min(this.memberPageNum, pages) })
    },
    async saveCoach(payload) {
      if (payload.id) await adminApi.updateCoach(payload.id, payload)
      else await adminApi.createCoach(payload)
      const total = Math.max(this.coachTotal + (payload.id ? 0 : 1), 0)
      const pages = Math.max(Math.ceil(total / this.coachPageSize), 1)
      await this.loadCoachPage({ pageNum: Math.min(this.coachPageNum, pages) })
    },
    async removeCoach(id) {
      await adminApi.deleteCoach(id)
      const total = Math.max(this.coachTotal - 1, 0)
      const pages = Math.max(Math.ceil(total / this.coachPageSize), 1)
      await this.loadCoachPage({ pageNum: Math.min(this.coachPageNum, pages) })
    },
    async saveCourse(payload) {
      const course = {
        ...payload,
        startTime: normalizeDateTime(payload.startTime),
        endTime: normalizeDateTime(payload.endTime),
      }
      if (payload.id) await adminApi.updateCourse(payload.id, course)
      else await adminApi.createCourse(course)
      await this.loadCoursePage()
    },
    async removeCourse(id) {
      await adminApi.deleteCourse(id)
      const total = Math.max(this.courseTotal - 1, 0)
      const pages = Math.max(Math.ceil(total / this.coursePageSize), 1)
      await this.loadCoursePage({ pageNum: Math.min(this.coursePageNum, pages) })
    },
    async reserveCourse(courseId) {
      await memberApi.reserve(courseId)
      await this.loadMemberData()
      return true
    },
    async waitlistCourse(courseId) {
      await memberApi.waitlist(courseId)
      await this.loadMemberData()
      return true
    },
    async confirmWaitlist(id) {
      await memberApi.confirmWaitlist(id)
      await this.loadMemberData()
    },
    async declineWaitlist(id) {
      await memberApi.declineWaitlist(id)
      await this.loadMemberData()
    },
    async cancelAppointment(id, admin = false) {
      if (admin) {
        await adminApi.cancelAppointment(id)
        await this.loadAdminData()
      } else {
        await memberApi.cancelAppointment(id)
        await this.loadMemberData()
      }
      return true
    },
    async updateProfile(payload) {
      await memberApi.updateProfile(payload)
      await this.loadMemberData()
    },
    async updatePassword(payload) {
      await memberApi.updatePassword(payload)
    },
  },
})
