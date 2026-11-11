<template>
  <div class="panel page-panel">
    <div class="toolbar">
      <el-input v-model="keyword" clearable placeholder="按姓名或手机号查询" :prefix-icon="Search" @keyup.enter="handleSearch" @clear="handleSearch" />
      <div class="section-actions">
        <el-button :icon="Search" @click="handleSearch">查询</el-button>
        <el-button type="primary" :icon="Plus" @click="openDialog()">新增会员</el-button>
      </div>
    </div>

    <el-table :data="filteredRows" style="width: 100%">
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column prop="username" label="登录账号" />
      <el-table-column prop="gender" label="性别" width="90" />
      <el-table-column prop="age" label="年龄" width="80" />
      <el-table-column prop="cardType" label="会员卡" />
      <el-table-column prop="expireTime" label="到期时间" />
      <el-table-column label="会员卡状态" width="110">
        <template #default="{ row }">
          <el-tag :type="membershipStatus(row).type">{{ membershipStatus(row).label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '正常' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button text type="success" @click="renew(row)">续费</el-button>
          <el-button text type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="table-pagination"
      v-model:current-page="pageNum"
      v-model:page-size="pageSize"
      :page-sizes="[5, 10, 20, 50]"
      :total="gymStore.memberTotal"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="handlePageChange"
      @size-change="handleSizeChange"
    />

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑会员' : '新增会员'" width="560px">
      <el-form :model="form" label-width="104px">
        <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.gender">
            <el-radio-button label="男" />
            <el-radio-button label="女" />
          </el-radio-group>
        </el-form-item>
        <el-form-item label="年龄"><el-input-number v-model="form.age" :min="1" :max="100" /></el-form-item>
        <el-form-item label="会员卡"><el-input v-model="form.cardType" /></el-form-item>
        <el-form-item label="到期时间"><el-date-picker v-model="form.expireTime" value-format="YYYY-MM-DD" /></el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="正常" inactive-text="禁用" />
        </el-form-item>
        <el-form-item label="登录账号">
          <el-input v-model="form.username" placeholder="会员登录用户名" />
        </el-form-item>
        <el-form-item label="登录密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="form.id ? '不修改请留空' : '请填写登录密码'"
          />
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
import { adminApi } from '@/api/gym'
import { useGymStore } from '@/stores/gym'

const gymStore = useGymStore()
const keyword = ref('')
const pageNum = ref(1)
const pageSize = ref(10)
const dialogVisible = ref(false)
const form = reactive({})

const filteredRows = computed(() => gymStore.members)

function openDialog(row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(
    form,
    row
      ? { ...row, password: '' }
      : {
          name: '',
          phone: '',
          gender: '',
          age: '',
          cardType: '',
          expireTime: '',
          status: 1,
          username: '',
          password: '',
        },
  )
  dialogVisible.value = true
}

async function save() {
  await gymStore.saveMember({ ...form })
  dialogVisible.value = false
  ElMessage.success('保存成功')
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除会员 ${row.name}？`, '删除确认', { type: 'warning' })
  await gymStore.removeMember(row.id)
  ElMessage.success('删除成功')
}

async function renew(row) {
  const { value } = await ElMessageBox.prompt(
    `为 ${row.name} 续费几个月？`,
    '会员续费',
    {
      inputValue: '1',
      inputPattern: /^(?:[1-9]|[12]\d|3[0-6])$/,
      inputErrorMessage: '请输入 1—36 之间的整数',
    },
  )
  await adminApi.renewMember(row.id, Number(value))
  await loadMembers()
  ElMessage.success('续费成功')
}

function membershipStatus(row) {
  const expire = row.expireTime ? new Date(`${row.expireTime}T23:59:59`) : null
  if (!expire || Number.isNaN(expire.getTime())) return { label: '未设置', type: 'info' }
  const days = Math.ceil((expire.getTime() - Date.now()) / 86400000)
  if (days < 0) return { label: '已过期', type: 'danger' }
  if (days <= 7) return { label: '即将到期', type: 'warning' }
  return { label: '有效', type: 'success' }
}

async function loadMembers() {
  await gymStore.loadMemberPage({
    pageNum: pageNum.value,
    pageSize: pageSize.value,
    keyword: keyword.value.trim(),
  })
  pageNum.value = gymStore.memberPageNum
  pageSize.value = gymStore.memberPageSize
}

function handleSearch() {
  pageNum.value = 1
  loadMembers()
}

function handlePageChange(value) {
  pageNum.value = value
  loadMembers()
}

function handleSizeChange(value) {
  pageSize.value = value
  pageNum.value = 1
  loadMembers()
}

onMounted(() => loadMembers())
</script>
