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
