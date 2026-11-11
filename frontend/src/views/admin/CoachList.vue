<template>
  <div class="panel page-panel">
    <div class="toolbar">
      <el-input v-model="keyword" clearable placeholder="按教练姓名查询" :prefix-icon="Search" @keyup.enter="handleSearch" @clear="handleSearch" />
      <div class="section-actions">
        <el-button :icon="Search" @click="handleSearch">查询</el-button>
        <el-button type="primary" :icon="Plus" @click="openDialog()">新增教练</el-button>
      </div>
    </div>

    <el-table :data="filteredRows" style="width: 100%">
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column prop="specialty" label="擅长项目" />
      <el-table-column prop="entryDate" label="入职日期" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '在职' : '离职' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button text type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="table-pagination"
      v-model:current-page="pageNum"
      v-model:page-size="pageSize"
      :page-sizes="[5, 10, 20, 50]"
      :total="gymStore.coachTotal"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="handlePageChange"
      @size-change="handleSizeChange"
    />

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑教练' : '新增教练'" width="520px">
      <el-form :model="form" label-width="88px">
        <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="擅长项目"><el-input v-model="form.specialty" /></el-form-item>
        <el-form-item label="入职日期"><el-date-picker v-model="form.entryDate" value-format="YYYY-MM-DD" /></el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="在职" inactive-text="离职" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { useGymStore } from '@/stores/gym'

const gymStore = useGymStore()
const keyword = ref('')
const pageNum = ref(1)
const pageSize = ref(10)
const dialogVisible = ref(false)
const form = reactive({})

const filteredRows = computed(() => gymStore.coaches)

// 打开对话框（新增/编辑）
function openDialog(row) {
  Object.assign(form, row || { name: '', phone: '', specialty: '', entryDate: '', status: 1 })
  if (!row) delete form.id
  dialogVisible.value = true
}

// 保存（新增或编辑）
async function save() {
  await gymStore.saveCoach({ ...form })
  pageNum.value = gymStore.coachPageNum
  pageSize.value = gymStore.coachPageSize
  dialogVisible.value = false
  ElMessage.success('保存成功')
}

// 删除
async function remove(row) {
  await ElMessageBox.confirm(`确认删除教练 ${row.name}？`, '删除确认', { type: 'warning' })
  await gymStore.removeCoach(row.id)
  pageNum.value = gymStore.coachPageNum
  pageSize.value = gymStore.coachPageSize
  ElMessage.success('删除成功')
}

async function loadCoaches() {
  await gymStore.loadCoachPage({
    pageNum: pageNum.value,
    pageSize: pageSize.value,
    keyword: keyword.value.trim(),
  })
  pageNum.value = gymStore.coachPageNum
  pageSize.value = gymStore.coachPageSize
}

function handleSearch() {
  pageNum.value = 1
  loadCoaches()
}

function handlePageChange(value) {
  pageNum.value = value
  loadCoaches()
}

function handleSizeChange(value) {
  pageSize.value = value
  pageNum.value = 1
  loadCoaches()
}

onMounted(() => loadCoaches())
</script>
