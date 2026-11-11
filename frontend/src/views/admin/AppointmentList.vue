<template>
  <div class="panel page-panel">
    <div class="section-head appointment-heading">
      <div>
        <h2>预约管理</h2>
        <p>按预约状态分类查看和管理会员课程预约。</p>
      </div>
      <el-radio-group v-model="activeCategory" class="appointment-tabs">
        <el-radio-button value="all">
          全部 <span class="appointment-tab-count">{{ allRows.length }}</span>
        </el-radio-button>
        <el-radio-button value="upcoming">
          待上课 <span class="appointment-tab-count">{{ counts.upcoming }}</span>
        </el-radio-button>
        <el-radio-button value="ended">
          已结束 <span class="appointment-tab-count">{{ counts.ended }}</span>
        </el-radio-button>
        <el-radio-button value="canceled">
          已取消 <span class="appointment-tab-count">{{ counts.canceled }}</span>
        </el-radio-button>
      </el-radio-group>
    </div>

    <div class="toolbar appointment-toolbar">
      <el-input v-model="memberKeyword" clearable placeholder="按会员名查询" :prefix-icon="Search" />
      <el-input v-model="courseKeyword" clearable placeholder="按课程名查询" :prefix-icon="Search" />
    </div>

    <el-table :data="filteredRows" style="width: 100%" empty-text="当前分类暂无预约记录">
      <el-table-column prop="memberName" label="会员" />
      <el-table-column prop="courseName" label="课程" min-width="150" />
      <el-table-column prop="coachName" label="教练" />
      <el-table-column prop="courseTime" label="课程时间" min-width="160" />
      <el-table-column v-if="activeCategory === 'canceled'" prop="updateTime" label="取消时间" min-width="160" />
      <el-table-column v-else prop="createTime" label="预约时间" min-width="160" />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="appointmentStatus(row).type">{{ appointmentStatus(row).label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button
            text
            type="danger"
            :disabled="appointmentStatus(row).label !== '待上课'"
            @click="cancel(row)"
          >
            取消预约
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useGymStore } from '@/stores/gym'
import {
  appointmentCounts,
  appointmentStatus,
  categorizeAppointment,
  sortAppointments,
} from '@/utils/appointment'

const gymStore = useGymStore()
const memberKeyword = ref('')
const courseKeyword = ref('')
const activeCategory = ref('upcoming')
const allRows = computed(() => gymStore.appointmentRows)
const counts = computed(() => appointmentCounts(allRows.value))
const filteredRows = computed(() => {
  const rows = allRows.value.filter(
    (item) =>
      item.memberName.includes(memberKeyword.value.trim()) &&
      item.courseName.includes(courseKeyword.value.trim()) &&
      (activeCategory.value === 'all' ||
        categorizeAppointment(item) === activeCategory.value),
  )
  return activeCategory.value === 'all'
    ? rows
    : sortAppointments(rows, activeCategory.value)
})

async function cancel(row) {
  await ElMessageBox.confirm(`确认取消 ${row.memberName} 的 ${row.courseName}？`, '取消预约', { type: 'warning' })
  await gymStore.cancelAppointment(row.id, true)
  ElMessage.success('已取消预约')
}

onMounted(() => gymStore.loadAdminData())
</script>
