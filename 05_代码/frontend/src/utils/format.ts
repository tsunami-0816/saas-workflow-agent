/** 展示格式化工具 */

export function fmtTime(t?: string | null): string {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

/** 执行/节点状态 → Element Plus tag type */
export function statusTagType(status?: string): 'success' | 'danger' | 'warning' | 'info' | 'primary' {
  switch (status) {
    case 'SUCCESS':
    case 'published':
    case 'active':
      return 'success'
    case 'FAILED':
    case 'disabled':
      return 'danger'
    case 'RUNNING':
      return 'primary'
    case 'WAITING':
    case 'PENDING':
    case 'draft':
      return 'warning'
    case 'SKIPPED':
      return 'info'
    default:
      return 'info'
  }
}

export const EXEC_STATUS_TEXT: Record<string, string> = {
  RUNNING: '运行中',
  SUCCESS: '成功',
  FAILED: '失败',
  WAITING: '等待延时',
  PENDING: '待调度',
  SKIPPED: '已跳过'
}

export const VERSION_STATUS_TEXT: Record<string, string> = {
  draft: '草稿',
  published: '已发布',
  disabled: '已禁用'
}

export const FAIL_REASON_TEXT: Record<string, string> = {
  node_failed: '节点失败',
  engine_restart: '引擎重启收敛',
  engine_error: '引擎异常',
  engine_deadlock: '引擎死锁'
}

/** JSON 美化展示（失败则原文返回；一律走文本转义，不 v-html，防 XSS） */
export function prettyJson(raw?: string | null): string {
  if (!raw) return '-'
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}
