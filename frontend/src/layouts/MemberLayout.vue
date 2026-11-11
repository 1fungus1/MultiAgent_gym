<template>
  <el-container class="app-shell member-shell">
    <el-aside width="232px" class="side-nav">
      <div class="brand">
        <div class="brand-mark member-mark">M</div>
        <div>
          <div class="brand-name">健身会员中心</div>
          <div class="brand-subtitle">Member Portal</div>
        </div>
      </div>

      <el-menu router :default-active="$route.path" class="nav-menu">
        <el-menu-item index="/member/profile">
          <el-icon><House /></el-icon>
          <span>个人资料</span>
        </el-menu-item>
        <el-menu-item index="/member/course">
          <el-icon><Calendar /></el-icon>
          <span>课程列表</span>
        </el-menu-item>
        <el-menu-item index="/member/appointment">
          <el-icon><Tickets /></el-icon>
          <span>我的预约</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="top-bar">
        <div>
          <div class="page-title">{{ route.meta.title || '会员中心' }}</div>
          <div class="page-subtitle">查看资料、课程安排和我的预约</div>
        </div>
        <div class="user-actions">
          <el-tag type="primary" effect="light">会员</el-tag>
          <span class="username">{{ userStore.username }}</span>
          <NotificationCenter />
          <el-button :icon="SwitchButton" @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main-area">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { Calendar, House, SwitchButton, Tickets } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import NotificationCenter from '@/components/NotificationCenter.vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

function handleLogout() {
  userStore.logout()
  router.replace('/login')
}
</script>
