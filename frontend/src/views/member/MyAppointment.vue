<template>
  <div class="panel page-panel">
    <div class="section-head appointment-heading">
      <div>
        <h2>我的预约</h2>
        <p>分别查看待上课、已结束和已取消的预约记录。</p>
      </div>
      <el-radio-group v-model="activeCategory" class="appointment-tabs">
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

    <el-table :data="rows" style="width: 100%" :empty-text="emptyText">
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
      <el-table-column label="操作" width="210" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending_confirmation'">
            <el-button text type="primary" @click="confirmWaitlist(row)">确认名额</el-button>
            <el-button text type="info" @click="declineWaitlist(row)">放弃</el-button>
          </template>
          <el-button
            v-else-if="row.status === 'waitlisted'"
            text
            type="warning"
            @click="declineWaitlist(row)"
          >
            退出候补
          </el-button>
          <el-button
            v-else-if="activeCategory === 'upcoming' && row.status === 'reserved'"
            text
            type="danger"
            :disabled="!canCancel(row)"
            @click="cancel(row)"
          >
            取消预约
          </el-button>
          <el-button
            v-else-if="isRebookable(row)"
            text
            type="primary"
            @click="rebook(row)"
          >
            重新预约
          </el-button>
          <span v-else class="appointment-no-action">—</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useGymStore } from '@/stores/gym'
import {
  appointmentCounts,
  appointmentStatus,
  categorizeAppointment,
  isRebookable,
  sortAppointments,
} from '@/utils/appointment'

const gymStore = useGymStore()
const activeCategory = ref('upcoming')
const allRows = computed(() => gymStore.myAppointments)
const counts = computed(() => appointmentCounts(allRows.value))
const rows = computed(() =>
  sortAppointments(
    allRows.value.filter(
      (item) => categorizeAppointment(item) === activeCategory.value,
    ),
    activeCategory.value,
  ),
)
const emptyText = computed(
  () =>
    ({
      upcoming: '暂无待上课预约',
      ended: '暂无已结束预约',
      canceled: '暂无已取消预约',
    })[activeCategory.value],
)

function canCancel(row) {
  return appointmentStatus(row).label === '待上课'
}

async function cancel(row) {
  await ElMessageBox.confirm(`确认取消 ${row.courseName}？`, '取消预约', { type: 'warning' })
  await gymStore.cancelAppointment(row.id)
  ElMessage.success('已取消预约')
}

async function rebook(row) {
  await ElMessageBox.confirm(`确认重新预约 ${row.courseName}？`, '重新预约', { type: 'warning' })
  await gymStore.reserveCourse(row.courseId)
  activeCategory.value = 'upcoming'
  ElMessage.success('重新预约成功')
}

async function confirmWaitlist(row) {
  await ElMessageBox.confirm(`确认接受 ${row.courseName} 的候补名额？`, '确认候补', { type: 'warning' })
  await gymStore.confirmWaitlist(row.id)
  ElMessage.success('候补预约已确认')
}

async function declineWaitlist(row) {
  await ElMessageBox.confirm(`确认放弃 ${row.courseName} 的候补？`, '退出候补', { type: 'warning' })
  await gymStore.declineWaitlist(row.id)
  ElMessage.success('已退出候补')
}

onMounted(() => gymStore.loadMemberData())
</script>
