const BASE_URL = '/api'

/**
 * 通过 SSE 调用领域智能体接口（支持会话记忆）
 * @param {string} message 用户消息
 * @param {AbortSignal} signal 取消信号
 * @param {string} sessionId 会话 ID，用于恢复历史
 */
export function doChat(message, signal, sessionId = '') {
  const params = new URLSearchParams({ message })
  if (sessionId) params.set('session_id', sessionId)
  return fetch(`${BASE_URL}/chat?${params}`, {
    method: 'GET',
    headers: { Accept: 'text/event-stream' },
    signal
  })
}

export { doChat as doChatWithManus }

/**
 * 删除后端指定会话的全部数据
 * @param {string} sessionId
 */
export async function deleteHistoryBackend(sessionId) {
  if (!sessionId) return
  try {
    await fetch(`${BASE_URL}/chat/history?session_id=${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
  } catch {}
}

/**
 * 从后端加载聊天历史记录（替代 localStorage）
 * @param {string} sessionId
 * @returns {Promise<Array>}
 */
export async function fetchHistory(sessionId) {
  if (!sessionId) return []
  try {
    const res = await fetch(`${BASE_URL}/chat/history?session_id=${encodeURIComponent(sessionId)}`)
    if (!res.ok) return []
    return await res.json()
  } catch {
    return []
  }
}

/**
 * 保存聊天历史记录到后端
 * @param {string} sessionId
 * @param {Array} messages
 */
export async function saveHistory(sessionId, messages) {
  if (!sessionId) return
  try {
    await fetch(`${BASE_URL}/chat/history?session_id=${encodeURIComponent(sessionId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages }),
    })
  } catch {}
}
