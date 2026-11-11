<template>
  <div class="page-panel report-page">
    <div class="section-head">
      <div>
        <h2>运营日报</h2>
        <p>{{ report.date || '今日' }} 课程、预约、签到与会员运营数据</p>
      </div>
      <el-button :loading="loading" @click="loadReport">刷新</el-button>
    </div>

    <div class="report-metrics">
      <article v-for="item in metrics" :key="item.label" class="panel report-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </article>
    </div>

    <section class="panel">
      <div class="section-head">
        <h2>今日课程</h2>
        <el-tag>{{ report.courseCount || 0 }} 门</el-tag>
      </div>
      <el-table :data="report.courses || []" empty-text="今日暂无课程">
        <el-table-column prop="name" label="课程" min-width="150" />
        <el-table-column prop="coachName" label="教练" />
        <el-table-column prop="startTime" label="时间" min-width="150" />
        <el-table-column label="预约/容量">
          <template #default="{ row }">{{ row.reserved }}/{{ row.capacity }}</template>
        </el-table-column>
        <el-table-column prop="checkedIn" label="签到" width="80" />
        <el-table-column prop="noShow" label="爽约" width="80" />
        <el-table-column prop="waitlisted" label="候补" width="80" />
      </el-table>
    </section>

    <section class="panel">
      <div class="section-head">
        <h2>今日用户预约活动</h2>
        <el-tag :type="report.activitySource === 'appointment_log' ? 'success' : 'warning'">
          {{ activitySourceLabel }}
        </el-tag>
      </div>
      <el-table :data="report.appointmentActivity || []" empty-text="今日暂无预约操作">
        <el-table-column prop="time" label="时间" min-width="160" />
        <el-table-column prop="memberName" label="会员" />
        <el-table-column label="操作" width="110">
          <template #default="{ row }">{{ actionLabel(row.action) }}</template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" min-width="260" />
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { adminApi } from '@/api/gym'

const loading = ref(false)
const report = ref({})
const metrics = computed(() => [
  { label: '今日课程', value: report.value.courseCount || 0, hint: `${report.value.fullCourseCount || 0} 门满员` },
  { label: '有效预约', value: report.value.reservedCount || 0, hint: `占用率 ${report.value.occupancyRate || 0}%` },
  { label: '已签到', value: report.value.checkedInCount || 0, hint: `出勤率 ${report.value.attendanceRate || 0}%` },
  { label: '候补人数', value: report.value.waitlistCount || 0, hint: '等待空余名额' },
  { label: '爽约人数', value: report.value.noShowCount || 0, hint: '未完成签到' },
  { label: '即将到期', value: report.value.expiringMemberCount || 0, hint: `已过期 ${report.value.expiredMemberCount || 0}` },
])
const activitySourceLabel = computed(() => {
  const labels = {
    appointment_log: '正式操作日志',
    legacy_inference: '旧数据推断',
    appointment_log_plus_inference: '日志 + 旧数据推断',
  }
  return labels[report.value.activitySource] || '未知来源'
})

async function loadReport() {
  loading.value = true
  try {
    report.value = (await adminApi.dailyReport()) || {}
  } finally {
    loading.value = false
  }
}

function actionLabel(action) {
  return {
    reserve: '预约',
    cancel: '取消',
    change: '改约',
    update: '更新',
    waitlist: '加入候补',
    waitlist_offer: '候补递补',
    waitlist_confirm: '确认候补',
    waitlist_decline: '放弃候补',
    waitlist_expire: '候补超时',
    checkin: '签到',
    no_show: '爽约',
  }[action] || action
}

onMounted(loadReport)
</script>

