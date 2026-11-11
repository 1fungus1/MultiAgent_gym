function parseDateTime(value) {
  if (!value) return null
  if (value instanceof Date) return value
  const parsed = new Date(String(value).replace(' ', 'T'))
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function categorizeAppointment(item, now = new Date()) {
  if (item.status === 'canceled') return 'canceled'
  if (item.status === 'no_show') return 'ended'
  const endTime = parseDateTime(item.courseEndTime)
  if (endTime && endTime.getTime() < now.getTime()) return 'ended'
  return 'upcoming'
}

export function appointmentStatus(item, now = new Date()) {
  const category = categorizeAppointment(item, now)
  if (category === 'canceled') {
    return { label: '已取消', type: 'info' }
  }
  if (category === 'ended') {
    if (item.status === 'no_show') {
      return { label: '爽约', type: 'danger' }
    }
    if (item.status === 'checked_in') {
      return { label: '已签到', type: 'success' }
    }
    return { label: '已结束', type: 'info' }
  }
  if (item.status === 'waitlisted') {
    return { label: '候补中', type: 'warning' }
  }
  if (item.status === 'pending_confirmation') {
    return { label: '候补待确认', type: 'warning' }
  }
  if (item.status === 'checked_in') {
    return { label: '已签到', type: 'success' }
  }
  const startTime = parseDateTime(item.courseTime)
  const endTime = parseDateTime(item.courseEndTime)
  if (
    startTime &&
    endTime &&
    startTime.getTime() <= now.getTime() &&
    endTime.getTime() >= now.getTime()
  ) {
    return { label: '进行中', type: 'warning' }
  }
  return { label: '待上课', type: 'success' }
}

export function sortAppointments(rows, category) {
  return [...rows].sort((left, right) => {
    if (category === 'upcoming') {
      return (
        (parseDateTime(left.courseTime)?.getTime() || 0) -
        (parseDateTime(right.courseTime)?.getTime() || 0)
      )
    }
    const leftTime =
      parseDateTime(left.updateTime)?.getTime() ||
      parseDateTime(left.courseTime)?.getTime() ||
      0
    const rightTime =
      parseDateTime(right.updateTime)?.getTime() ||
      parseDateTime(right.courseTime)?.getTime() ||
      0
    return rightTime - leftTime
  })
}

export function appointmentCounts(rows, now = new Date()) {
  const counts = { upcoming: 0, ended: 0, canceled: 0 }
  rows.forEach((item) => {
    counts[categorizeAppointment(item, now)] += 1
  })
  return counts
}

export function isRebookable(item, now = new Date()) {
  if (item.status !== 'canceled') return false
  const endTime = parseDateTime(item.courseEndTime)
  return Boolean(endTime && endTime.getTime() > now.getTime())
}
