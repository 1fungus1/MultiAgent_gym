import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/stores/user'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

request.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    const result = response.data
    if (!result || typeof result.code === 'undefined') {
      return result
    }
    if (result.code === 200) {
      return result.data
    }
    if (result.code === 401) {
      const userStore = useUserStore()
      userStore.logout()
      router.replace('/login')
    }
    if (!response.config.silent) {
      ElMessage.error(result.message || '请求失败')
    }
    return Promise.reject(result)
  },
  (error) => {
    const message = error.response?.data?.message || error.message || '网络异常'
    if (!error.config?.silent) {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  },
)

export default request
