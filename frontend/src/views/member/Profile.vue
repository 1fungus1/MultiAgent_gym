<template>
  <div class="dashboard-page">
    <section class="member-hero">
      <div>
        <el-tag type="primary">{{ profile.cardType }}</el-tag>
        <h1>{{ profile.name }}，欢迎回来</h1>
        <p>
          会员卡有效期至 {{ profile.expireTime }}。
          <el-tag :type="membershipStatus.type" size="small">{{ membershipStatus.label }}</el-tag>
        </p>
      </div>
    </section>

    <section class="content-grid">
      <div class="panel">
        <div class="section-head">
          <h2>个人资料</h2>
          <div class="section-actions">
            <el-tag :type="profile.status === 1 ? 'success' : 'info'">{{ profile.status === 1 ? '正常' : '禁用' }}</el-tag>
            <el-button type="primary" plain :icon="Edit" @click="openProfileDialog">编辑资料</el-button>
          </div>
        </div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="姓名">{{ profile.name }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ profile.phone }}</el-descriptions-item>
          <el-descriptions-item label="性别">{{ profile.gender }}</el-descriptions-item>
          <el-descriptions-item label="年龄">{{ profile.age }}</el-descriptions-item>
          <el-descriptions-item label="会员卡">{{ profile.cardType }}</el-descriptions-item>
          <el-descriptions-item label="到期时间">{{ profile.expireTime }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="panel">
        <div class="section-head">
          <h2>账号安全</h2>
          <el-button type="primary" plain :icon="Lock" @click="openPasswordDialog">修改密码</el-button>
        </div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="登录账号">{{ userStore.username }}</el-descriptions-item>
          <el-descriptions-item label="密码状态">已设置</el-descriptions-item>
        </el-descriptions>
      </div>
    </section>

    <el-dialog v-model="profileDialogVisible" title="编辑资料" width="520px">
      <el-form :model="form" label-width="88px">
        <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="年龄"><el-input-number v-model="form.age" :min="1" :max="100" /></el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.gender">
            <el-radio-button label="男" />
            <el-radio-button label="女" />
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="profileDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveProfile">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="520px">
      <el-form :model="passwordForm" label-width="88px">
        <el-form-item label="旧密码">
          <el-input v-model="passwordForm.oldPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.newPassword" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="savePassword">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Edit, Lock } from '@element-plus/icons-vue'
import { useGymStore } from '@/stores/gym'
import { useUserStore } from '@/stores/user'

const gymStore = useGymStore()
const userStore = useUserStore()
const profile = computed(() => gymStore.currentMember || {})
const membershipStatus = computed(() => {
  if (!profile.value.expireTime) return { label: '未设置有效期', type: 'info' }
  const expire = new Date(`${profile.value.expireTime}T23:59:59`)
  const days = Math.ceil((expire.getTime() - Date.now()) / 86400000)
  if (days < 0) return { label: '已过期，请续费', type: 'danger' }
  if (days <= 7) return { label: `仅剩 ${days} 天`, type: 'warning' }
  return { label: '会员有效', type: 'success' }
})
const profileDialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const form = reactive({ phone: '', age: '', gender: '' })
const passwordForm = reactive({ oldPassword: '', newPassword: '' })

function resetForm() {
  Object.assign(form, {
    phone: profile.value.phone,
    age: profile.value.age,
    gender: profile.value.gender,
  })
}

function openProfileDialog() {
  resetForm()
  profileDialogVisible.value = true
}

function openPasswordDialog() {
  passwordForm.oldPassword = ''
  passwordForm.newPassword = ''
  passwordDialogVisible.value = true
}

async function saveProfile() {
  await gymStore.updateProfile({ ...form })
  profileDialogVisible.value = false
  ElMessage.success('资料已保存')
}

async function savePassword() {
  await gymStore.updatePassword({ ...passwordForm })
  passwordDialogVisible.value = false
  ElMessage.success('密码已修改')
}

onMounted(async () => {
  await gymStore.loadMemberData()
  resetForm()
})
</script>
