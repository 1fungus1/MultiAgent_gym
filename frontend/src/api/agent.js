import request from '@/utils/request'

export function chatWithMainAgent(data) {
  return request.post('/agent/chat', data, {
    timeout: 90000,
    silent: true,
  })
}

