<template>
  <main class="login-page">
    <section class="login-visual">
      <div class="login-hero">
        <el-tag effect="dark" type="success">Gym Manager</el-tag>
        <h1>健身房管理系统</h1>
        <p>管理会员、教练与课程<br />让预约、签到和日常运营更轻松</p>
      </div>
      <div class="login-preview">
        <div class="preview-header">
          <span>今日运营</span>
          <strong>18:30 热门课程</strong>
        </div>
        <div class="preview-grid">
          <div>
            <strong>128</strong>
            <span>活跃会员</span>
          </div>
          <div>
            <strong>12</strong>
            <span>在职教练</span>
          </div>
          <div>
            <strong>36</strong>
            <span>本周预约</span>
          </div>
        </div>
      </div>
    </section>

    <section class="login-panel">
      <div class="panel-title">
        <h2>账号登录</h2>
        <p>请输入账号和密码进入系统。</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            placeholder="密码"
            type="password"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>
        <el-button type="primary" class="login-button" :loading="loading" @click="handleLogin">
          登录
        </el-button>
      </el-form>

    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { login } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function goHome(role) {
  router.replace(role === 'admin' ? '/admin/dashboard' : '/member/profile')
}

async function handleLogin() {
  await formRef.value.validate()
  loading.value = true
  try {
    const user = await login({ username: form.username, password: form.password })
    userStore.setUser(user)
    ElMessage.success('登录成功')
    goHome(user.role)
  } catch (err){
  // 捕获接口异常，弹窗展示后端返回的错误信息
  const errMsg = err?.message || err?.response?.data?.message || '请求失败，请检查后端服务'
  ElMessage.error(errMsg)
} finally {
  loading.value = false
}
}
</script>
