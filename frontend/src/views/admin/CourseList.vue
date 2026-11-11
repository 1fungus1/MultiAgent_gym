<template>
  <div class="panel page-panel">
    <div class="toolbar">
      <el-input v-model="keyword" clearable placeholder="按课程名称查询" :prefix-icon="Search" @keyup.enter="handleSearch" @clear="handleSearch" />
      <div class="section-actions">
        <el-button :icon="Search" @click="handleSearch">查询</el-button>
        <el-button type="primary" :icon="Plus" @click="openDialog()">新增课程</el-button>
      </div>
    </div>

    <el-table :data="filteredRows" style="width: 100%">
      <el-table-column prop="name" label="课程名称" min-width="140" />
      <el-table-column prop="type" label="类型" width="90" />
      <el-table-column prop="coachName" label="教练" width="100" />
      <el-table-column prop="startTime" label="开始时间" min-width="160" />
      <el-table-column prop="endTime" label="结束时间" min-width="160" />
      <el-table-column label="时间状态" width="100">
        <template #default="{ row }">
          <el-tag :type="timeStatusType(row.timeStatus)">{{ row.timeStatus || '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="容量" width="100">
        <template #default="{ row }">{{ row.bookedCount }}/{{ row.capacity }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '可预约' : '停课' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" :disabled="row.timeStatus === '已结束'" @click="openDialog(row)">编辑</el-button>
          <el-button text type="success" @click="openCheckinCode(row)">签到码</el-button>
          <el-button text type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="table-pagination"
      v-model:current-page="pageNum"
      v-model:page-size="pageSize"
      :page-sizes="[5, 10, 20, 50]"
      :total="gymStore.courseTotal"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="handlePageChange"
      @size-change="handleSizeChange"
    />

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑课程' : '新增课程'" width="620px">
      <el-form :model="form" label-width="88px">
        <el-form-item label="课程名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型"><el-input v-model="form.type" /></el-form-item>
        <el-form-item label="授课教练">
          <el-select v-model="form.coachId" placeholder="请选择教练">
            <el-option v-for="coach in gymStore.coaches" :key="coach.id" :label="coach.name" :value="coach.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="form.startTime" type="datetime" value-format="YYYY-MM-DD HH:mm" :disabled-date="disablePastDate" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker v-model="form.endTime" type="datetime" value-format="YYYY-MM-DD HH:mm" :disabled-date="disablePastDate" />
        </el-form-item>
        <el-form-item label="人数上限"><el-input-number v-model="form.capacity" :min="1" :max="200" /></el-form-item>
        <el-form-item label="已预约"><el-input-number v-model="form.bookedCount" :min="0" :max="form.capacity || 200" /></el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="可预约" inactive-text="停课" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="checkinDialogVisible"
      :title="`${checkinCode?.courseName || ''} · 签到码`"
      width="430px"
      @closed="stopCheckinRefresh"
    >
      <div v-loading="checkinLoading" class="checkin-code-panel">
        <img v-if="checkinCode?.qrCode" :src="checkinCode.qrCode" alt="课程签到二维码" />
        <p>会员使用手机扫描二维码完成签到。二维码每 25 秒自动刷新。</p>
        <el-tag type="warning">当前签到码最长有效 45 秒</el-tag>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { adminApi } from '@/api/gym'
import { useGymStore } from '@/stores/gym'

const gymStore = useGymStore()
const keyword = ref('')
const pageNum = ref(1)
const pageSize = ref(10)
const dialogVisible = ref(false)
const form = reactive({})
const checkinDialogVisible = ref(false)
const checkinLoading = ref(false)
const checkinCode = ref(null)
let checkinTimer = null

const filteredRows = computed(() => gymStore.courseRows)

function timeStatusType(value) {
  if (value === '未开始') return 'primary'
  if (value === '进行中') return 'success'
  if (value === '已结束') return 'info'
  return 'warning'
}

function disablePastDate(date) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return date.getTime() < today.getTime()
}

function parseDateTime(value) {
  if (!value) return null
  if (value instanceof Date) return value
  return new Date(value.replace(' ', 'T'))
}

function openDialog(row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(
    form,
    row || {
      name: '',
      type: '',
      coachId: gymStore.coaches[0]?.id,
      startTime: '',
      endTime: '',
      capacity: 20,
      bookedCount: 0,
      status: 1,
    },
  )
  dialogVisible.value = true
}

async function save() {
  const startTime = parseDateTime(form.startTime)
  if (startTime && startTime.getTime() < Date.now()) {
    ElMessage.error('课程开始时间不能早于当前时间')
    return
  }
  await gymStore.saveCourse({ ...form })
  pageNum.value = gymStore.coursePageNum
  dialogVisible.value = false
  ElMessage.success('保存成功')
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除课程 ${row.name}？`, '删除确认', { type: 'warning' })
  await gymStore.removeCourse(row.id)
  pageNum.value = gymStore.coursePageNum
  ElMessage.success('删除成功')
}

async function openCheckinCode(row) {
  checkinDialogVisible.value = true
  await loadCheckinCode(row.id)
  stopCheckinRefresh()
  checkinTimer = window.setInterval(() => loadCheckinCode(row.id), 25000)
}

async function loadCheckinCode(courseId) {
  checkinLoading.value = true
  try {
    checkinCode.value = await adminApi.checkinCode(courseId)
  } finally {
    checkinLoading.value = false
  }
}

function stopCheckinRefresh() {
  if (checkinTimer) {
    window.clearInterval(checkinTimer)
    checkinTimer = null
  }
}

async function loadCourses() {
  await gymStore.loadCoursePage({
    pageNum: pageNum.value  ,
    pageSize: pageSize.value,
    keyword: keyword.value.trim(),
  })
  pageNum.value = gymStore.coursePageNum
  pageSize.value = gymStore.coursePageSize
}

function handleSearch() {
  pageNum.value = 1
  loadCourses()
}

function handlePageChange(value) {
  pageNum.value = value
  loadCourses()
}

function handleSizeChange(value) {
  pageSize.value = value
  pageNum.value = 1
  loadCourses()
}

onMounted(async () => {
  await Promise.all([gymStore.loadCoaches(), loadCourses()])
})

onBeforeUnmount(stopCheckinRefresh)
</script>
