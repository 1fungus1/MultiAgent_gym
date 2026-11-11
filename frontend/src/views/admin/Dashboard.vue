<template>
  <div class="dashboard-page">
    <section class="metric-grid">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="metric-icon" :class="item.className">
          <el-icon><component :is="item.icon" /></el-icon>
        </div>
        <div>
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.hint }}</small>
        </div>
      </div>
    </section>

    <section class="content-grid">
      <div class="panel chart-panel">
        <div class="section-head">
          <h2>本周预约趋势</h2>
          <el-tag>业务数据</el-tag>
        </div>
        <div ref="chartRef" class="chart"></div>
      </div>

      <div class="panel">
        <div class="section-head">
          <h2>今日课程</h2>
          <el-button text type="primary">查看全部</el-button>
        </div>
        <el-table :data="todayCourses" style="width: 100%">
          <el-table-column prop="time" label="时间" width="92" />
          <el-table-column prop="name" label="课程" />
          <el-table-column prop="coach" label="教练" width="90" />
          <el-table-column prop="booked" label="预约" width="82" />
        </el-table>
      </div>
    </section>

    <section class="panel">
      <div class="section-head">
        <h2>最近预约</h2>
        <el-button type="primary" plain>刷新</el-button>
      </div>
      <el-table :data="recentAppointments" style="width: 100%">
        <el-table-column prop="member" label="会员" />
        <el-table-column prop="course" label="课程" />
        <el-table-column prop="time" label="预约时间" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === '已预约' ? 'success' : 'info'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, markRaw, onMounted, ref } from 'vue'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { Calendar, Medal, Tickets, User } from '@element-plus/icons-vue'
import { useGymStore } from '@/stores/gym'

const chartRef = ref()
const gymStore = useGymStore()

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const metrics = computed(() => [
  { label: '会员总数', value: gymStore.dashboard.memberCount, hint: '当前会员', icon: markRaw(User), className: 'blue' },
  { label: '教练总数', value: gymStore.dashboard.coachCount, hint: '在职教练', icon: markRaw(Medal), className: 'green' },
  { label: '课程总数', value: gymStore.dashboard.courseCount, hint: '当前课程', icon: markRaw(Calendar), className: 'orange' },
  { label: '预约总数', value: gymStore.dashboard.appointmentCount, hint: '有效预约', icon: markRaw(Tickets), className: 'purple' },
])

const todayCourses = computed(() =>
  gymStore.courseRows.slice(0, 3).map((item) => ({
    time: item.startTime.slice(11, 16),
    name: item.name,
    coach: item.coachName,
    booked: `${item.bookedCount}/${item.capacity}`,
  })),
)

const recentAppointments = computed(() =>
  gymStore.appointmentRows.slice(0, 5).map((item) => ({
    member: item.memberName,
    course: item.courseName,
    time: item.createTime,
    status: item.status === 'reserved' ? '已预约' : '已取消',
  })),
)

onMounted(() => {
  gymStore.loadAdminData()
  const chart = echarts.init(chartRef.value)
  chart.setOption({
    grid: { left: 32, right: 16, top: 28, bottom: 28 },
    xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#e5e7eb' } } },
    tooltip: { trigger: 'axis' },
    series: [
      {
        data: [0, 0, 0, 0, 0, 0, 0],
        type: 'bar',
        barWidth: 26,
        itemStyle: { color: '#2563eb', borderRadius: [6, 6, 0, 0] },
      },
    ],
  })
  window.addEventListener('resize', () => chart.resize())
})
</script>
