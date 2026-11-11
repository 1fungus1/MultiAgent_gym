import request from '@/utils/request'

export const notificationApi = {
  list: () => request.get('/notifications', { params: { limit: 30 } }),
  markRead: (id) => request.put(`/notifications/${id}/read`),
  markAllRead: () => request.put('/notifications/read-all'),
}

