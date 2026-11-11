<template>
  <el-popover placement="bottom-end" :width="360" trigger="click" @show="loadNotifications">
    <template #reference>
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
        <el-button class="notification-button" :icon="Bell" circle aria-label="通知中心" />
      </el-badge>
    </template>

    <div class="notification-panel">
      <div class="notification-head">
        <strong>通知中心</strong>
        <el-button text size="small" :disabled="unreadCount === 0" @click="markAllRead">全部已读</el-button>
      </div>
      <div v-loading="loading" class="notification-list">
        <button
          v-for="item in notifications"
          :key="item.id"
          type="button"
          class="notification-item"
          :class="{ 'notification-unread': !item.isRead }"
          @click="openNotification(item)"
        >
          <span class="notification-dot" />
          <span class="notification-copy">
            <strong>{{ item.title }}</strong>
            <span>{{ item.content }}</span>
            <time>{{ item.createTime }}</time>
          </span>
        </button>
        <el-empty v-if="!loading && notifications.length === 0" description="暂无通知" :image-size="72" />
      </div>
    </div>
  </el-popover>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Bell } from '@element-plus/icons-vue'
import { notificationApi } from '@/api/notification'

const loading = ref(false)
const notifications = ref([])
const unreadCount = ref(0)
let refreshTimer = null

async function loadNotifications() {
  loading.value = true
  try {
    const result = await notificationApi.list()
    notifications.value = result?.records || []
    unreadCount.value = result?.unreadCount || 0
  } finally {
    loading.value = false
  }
}

async function openNotification(item) {
  if (!item.isRead) {
    await notificationApi.markRead(item.id)
    item.isRead = true
    unreadCount.value = Math.max(unreadCount.value - 1, 0)
  }
}

async function markAllRead() {
  await notificationApi.markAllRead()
  notifications.value.forEach((item) => {
    item.isRead = true
  })
  unreadCount.value = 0
}

onMounted(() => {
  loadNotifications()
  refreshTimer = window.setInterval(loadNotifications, 30000)
})

onBeforeUnmount(() => {
  if (refreshTimer) window.clearInterval(refreshTimer)
})
</script>
