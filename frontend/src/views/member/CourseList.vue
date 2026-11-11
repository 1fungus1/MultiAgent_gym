<template>
  <div class="panel page-panel">
    <div class="toolbar toolbar-wide">
      <el-input v-model="keyword" clearable placeholder="按课程名称查询" :prefix-icon="Search" />
      <el-select v-model="type" clearable placeholder="课程类型">
        <el-option v-for="item in types" :key="item" :label="item" :value="item" />
      </el-select>
    </div>

    <el-table :data="filteredRows" style="width: 100%">
      <el-table-column prop="name" label="课程名称" min-width="140" />
      <el-table-column prop="type" label="类型" width="90" />
      <el-table-column prop="coachName" label="教练" width="100" />
      <el-table-column prop="startTime" label="开始时间" min-width="160" />
      <el-table-column label="容量" width="100">
        <template #default="{ row }">{{ row.bookedCount }}/{{ row.capacity }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="courseAvailable(row) ? 'success' : courseWaitlistable(row) ? 'warning' : 'info'">
            {{ courseAvailable(row) ? '可预约' : courseWaitlistable(row) ? '已满·可候补' : '不可预约' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button v-if="courseAvailable(row)" type="primary" plain @click="reserve(row)">预约</el-button>
          <el-button v-else-if="courseWaitlistable(row)" type="warning" plain @click="joinWaitlist(row)">加入候补</el-button>
          <span v-else class="appointment-no-action">—</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useGymStore } from '@/stores/gym'

const gymStore = useGymStore()
const keyword = ref('')
const type = ref('')
const types = computed(() => [...new Set(gymStore.courses.map((item) => item.type))])

const filteredRows = computed(() =>
  gymStore.courseRows.filter(
    (item) => item.name.includes(keyword.value.trim()) && (!type.value || item.type === type.value),
  ),
)

function courseAvailable(row) {
  const startTime = row.startTime ? new Date(row.startTime.replace(' ', 'T')) : null
  return row.status === 1 && row.remaining > 0 && startTime && startTime.getTime() > Date.now()
}

function courseWaitlistable(row) {
  return Boolean(row.canWaitlist)
}

async function reserve(row) {
  const ok = await gymStore.reserveCourse(row.id)
  ElMessage[ok ? 'success' : 'warning'](ok ? '预约成功' : '该课程不可预约或已重复预约')
}

async function joinWaitlist(row) {
  await gymStore.waitlistCourse(row.id)
  ElMessage.success('已加入候补队列，有名额时会通知你')
}

onMounted(() => gymStore.loadMemberData())
</script>
