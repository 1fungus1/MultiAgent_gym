<template>
  <el-container class="app-shell">
    <el-aside width="232px" class="side-nav">
      <div class="brand">
        <div class="brand-mark">G</div>
        <div>
          <div class="brand-name">健身房管理</div>
          <div class="brand-subtitle">Admin Console</div>
        </div>
      </div>

      <el-menu router :default-active="$route.path" class="nav-menu">
        <el-menu-item index="/admin/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>首页统计</span>
        </el-menu-item>
        <el-menu-item index="/admin/member">
          <el-icon><User /></el-icon>
          <span>会员管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/coach">
          <el-icon><Medal /></el-icon>
          <span>教练管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/course">
          <el-icon><Calendar /></el-icon>
          <span>课程管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/appointment">
          <el-icon><Tickets /></el-icon>
          <span>预约管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/report">
          <el-icon><Document /></el-icon>
          <span>运营日报</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="top-bar">
        <div>
          <div class="page-title">{{ route.meta.title || '管理后台' }}</div>
          <div class="page-subtitle">管理会员、教练、课程与预约数据</div>
        </div>
        <div class="user-actions">
          <el-tag type="success" effect="light">管理员</el-tag>
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
import { Calendar, DataAnalysis, Document, Medal, SwitchButton, Tickets, User } from '@element-plus/icons-vue'
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
