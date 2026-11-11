<template>
  <div class="panel page-panel checkin-page">
    <div class="checkin-hero">
      <div class="checkin-icon">✓</div>
      <h2>课程扫码签到</h2>
      <p>签到码来自当前课程的最新二维码。</p>
    </div>

    <el-result
      v-if="!token"
      icon="warning"
      title="缺少签到码"
      sub-title="请重新扫描管理员展示的课程二维码。"
    />
    <el-result
      v-else-if="result"
      icon="success"
      title="签到成功"
      :sub-title="`${result.courseName}，签到时间 ${result.checkedInAt}`"
    />
    <el-result
      v-else-if="errorMessage"
      icon="error"
      title="签到失败"
      :sub-title="errorMessage"
    />
    <div v-else class="checkin-action">
      <p>请确认你已到店，并点击下方按钮完成签到。</p>
      <el-button type="primary" size="large" :loading="loading" @click="submitCheckin">
        确认签到
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { memberApi } from '@/api/gym'

const route = useRoute()
const token = typeof route.query.token === 'string' ? route.query.token : ''
const loading = ref(false)
const errorMessage = ref('')
const result = ref(null)

async function submitCheckin() {
  loading.value = true
  errorMessage.value = ''
  try {
    result.value = await memberApi.checkIn(token)
  } catch (error) {
    errorMessage.value = error?.message || '签到失败，请扫描最新二维码。'
  } finally {
    loading.value = false
  }
}
</script>

