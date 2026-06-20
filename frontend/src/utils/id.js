/**
 * 生成唯一聊天室 ID
 */
export function generateChatId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `chat_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`
}
