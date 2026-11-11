import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: () => import('@/views/Login.vue') },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { role: 'admin' },
    redirect: '/admin/dashboard',
    children: [
      { path: 'dashboard', component: () => import('@/views/admin/Dashboard.vue'), meta: { title: '首页统计' } },
      { path: 'member', component: () => import('@/views/admin/MemberList.vue'), meta: { title: '会员管理' } },
      { path: 'coach', component: () => import('@/views/admin/CoachList.vue'), meta: { title: '教练管理' } },
      { path: 'course', component: () => import('@/views/admin/CourseList.vue'), meta: { title: '课程管理' } },
      { path: 'appointment', component: () => import('@/views/admin/AppointmentList.vue'), meta: { title: '预约管理' } },
      { path: 'report', component: () => import('@/views/admin/DailyReport.vue'), meta: { title: '运营日报' } },
    ],
  },
  {
    path: '/member',
    component: () => import('@/layouts/MemberLayout.vue'),
    meta: { role: 'member' },
    redirect: '/member/profile',
    children: [
      { path: 'profile', component: () => import('@/views/member/Profile.vue'), meta: { title: '个人资料' } },
      { path: 'course', component: () => import('@/views/member/CourseList.vue'), meta: { title: '课程列表' } },
      { path: 'appointment', component: () => import('@/views/member/MyAppointment.vue'), meta: { title: '我的预约' } },
      { path: 'checkin', component: () => import('@/views/member/CourseCheckin.vue'), meta: { title: '课程签到' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const userStore = useUserStore()
  if (to.path === '/login') {
    if (userStore.token && userStore.role === 'admin') return '/admin/dashboard'
    if (userStore.token && userStore.role === 'member') return '/member/profile'
    return true
  }

  const requiredRole = to.matched.find((item) => item.meta.role)?.meta.role
  if (!requiredRole) return true
  if (!userStore.token) return '/login'
  if (userStore.role !== requiredRole) {
    return userStore.role === 'admin' ? '/admin/dashboard' : '/member/profile'
  }
  return true
})

export default router
