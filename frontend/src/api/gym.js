import request from '@/utils/request'

export const adminApi = {
  dashboard: () => request.get('/admin/dashboard'),
  members: () => request.get('/admin/members'),
  memberPage: (params) => request.get('/admin/members/page', { params }),
  createMember: (data) => request.post('/admin/members', data),
  updateMember: (id, data) => request.put(`/admin/members/${id}`, data),
  renewMember: (id, months) => request.put(`/admin/members/${id}/renew`, { months }),
  deleteMember: (id) => request.delete(`/admin/members/${id}`),
  coaches: () => request.get('/admin/coaches'),
  coachPage: (params) => request.get('/admin/coaches/page', { params }),
  createCoach: (data) => request.post('/admin/coaches', data),
  updateCoach: (id, data) => request.put(`/admin/coaches/${id}`, data),
  deleteCoach: (id) => request.delete(`/admin/coaches/${id}`),
  courses: () => request.get('/admin/courses'),
  coursePage: (params) => request.get('/admin/courses/page', { params }),
  createCourse: (data) => request.post('/admin/courses', data),
  updateCourse: (id, data) => request.put(`/admin/courses/${id}`, data),
  deleteCourse: (id) => request.delete(`/admin/courses/${id}`),
  checkinCode: (id) => request.get(`/admin/courses/${id}/checkin-code`),
  appointments: () => request.get('/admin/appointments'),
  cancelAppointment: (id) => request.put(`/admin/appointments/${id}/cancel`),
  dailyReport: () => request.get('/admin/dashboard/daily-report'),
}

export const memberApi = {
  profile: () => request.get('/member/profile'),
  updateProfile: (data) => request.put('/member/profile', data),
  updatePassword: (data) => request.put('/member/profile/password', data),
  courses: () => request.get('/member/courses'),
  appointments: () => request.get('/member/appointments'),
  reserve: (courseId) => request.post('/member/appointments', { courseId }),
  waitlist: (courseId) => request.post('/member/appointments/waitlist', { courseId }),
  cancelAppointment: (id) => request.put(`/member/appointments/${id}/cancel`),
  confirmWaitlist: (id) => request.post(`/member/appointments/${id}/confirm-waitlist`),
  declineWaitlist: (id) => request.post(`/member/appointments/${id}/decline-waitlist`),
  checkIn: (token) => request.post('/member/appointments/check-in', { token }),
}
