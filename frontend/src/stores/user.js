import { defineStore } from 'pinia'

const STORAGE_KEY = 'gym_manager_user'

function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

export const useUserStore = defineStore('user', {
  state: () => {
    const stored = readStoredUser()
    return {
      token: stored.token || '',
      userId: stored.userId || '',
      username: stored.username || '',
      role: stored.role || '',
    }
  },
  actions: {
    setUser(user) {
      this.token = user.token
      this.userId = user.userId
      this.username = user.username
      this.role = user.role
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          token: this.token,
          userId: this.userId,
          username: this.username,
          role: this.role,
        }),
      )
    },
    logout() {
      this.token = ''
      this.userId = ''
      this.username = ''
      this.role = ''
      localStorage.removeItem(STORAGE_KEY)
    },
  },
})
