<template>
  <div class="chat-page">
    <header class="chat-header">
      <router-link to="/" class="back-btn">← 返回</router-link>
      <div class="header-info">
        <h1>{{ title }}</h1>
      </div>
      <div class="header-actions">
        <button class="history-btn" @click="showHistory = !showHistory" :disabled="loading">
          📋 {{ showHistory ? '关闭' : '历史' }}
        </button>
        <button class="new-chat-btn" @click="startNewChat" :disabled="loading">＋ 新对话</button>
      </div>
    </header>

    <!-- 历史对话列表 -->
    <div v-if="showHistory" class="history-panel">
      <div v-if="sessionHistory.length === 0" class="history-empty">暂无历史对话</div>
      <div
        v-for="(item, idx) in sessionHistory"
        :key="item.id"
        class="history-item"
        :class="{ active: item.id === sessionId.value }"
        @click="switchToSession(item.id)"
      >
        <div class="history-preview">{{ item.preview || '空对话' }}</div>
        <div class="history-time">{{ item.time }}</div>
        <button class="history-del" @click.stop="deleteHistory(idx)" title="删除">×</button>
      </div>
    </div>

    <ChatRoom
      :messages="messages"
      :loading="loading"
      :placeholder="placeholder"
      :show-mic="showMic"
      :pending-image="pendingImage"
      @send="handleSend"
      @mic-start="handleMicStart"
      @select-image="selectImage"
      @clear-image="clearImage"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChatRoom from '../components/ChatRoom.vue'
import { parseSseStream } from '../utils/sse.js'
import { fetchHistory, saveHistory, deleteHistoryBackend, doChatVision } from '../api/chat.js'

// 浏览器唯一标识（仅存在 localStorage，无聊天内容）
let userId = ''
try {
  userId = localStorage.getItem('_uid')
  if (!userId) {
    userId = 'u' + Math.random().toString(36).substring(2, 10)
    localStorage.setItem('_uid', userId)
  }
} catch {}

const HISTORY_KEY = 'chat_history_list'

const props = defineProps({
  title: { type: String, required: true },
  placeholder: { type: String, default: '输入消息，按 Enter 发送...' },
  showMic: { type: Boolean, default: false },
  chatFn: { type: Function, required: true },
})

// ====== 会话 ID ======
const savedSessionId = (() => {
  try { return localStorage.getItem('chat_session_id') } catch { return null }
})()
const sessionId = ref(savedSessionId || 'session_' + Math.random().toString(36).substring(2, 10))
try { localStorage.setItem('chat_session_id', sessionId.value) } catch {}

// ====== 历史对话列表（仅存 sessionId + 预览，无消息内容） ======
const showHistory = ref(false)
const sessionHistory = ref([])
try {
  const saved = localStorage.getItem(HISTORY_KEY)
  if (saved) sessionHistory.value = JSON.parse(saved)
} catch {}

function saveHistoryList() {
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(sessionHistory.value)) } catch {}
}

function addToHistory(id, preview) {
  // 去重（如果已存在则移到最前）
  sessionHistory.value = sessionHistory.value.filter(h => h.id !== id)
  sessionHistory.value.unshift({
    id,
    preview: preview.slice(0, 30),
    time: new Date().toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }),
  })
  // 只保留最近 20 条
  if (sessionHistory.value.length > 20) sessionHistory.value = sessionHistory.value.slice(0, 20)
  saveHistoryList()
}

function deleteHistory(idx) {
  const item = sessionHistory.value[idx]
  if (item) deleteHistoryBackend(item.id)  // 删除后端数据库记录
  sessionHistory.value.splice(idx, 1)
  saveHistoryList()
}

function startNewChat() {
  if (loading.value || messages.value.length === 0) return
  // 保存当前对话到后端
  saveHistory(sessionId.value, messages.value)
  // 加入历史列表
  const firstMsg = messages.value.find(m => m.role === 'user')
  addToHistory(sessionId.value, firstMsg?.content || '')
  // 生成新 session_id，清空对话
  sessionId.value = 'session_' + Math.random().toString(36).substring(2, 10)
  try { localStorage.setItem('chat_session_id', sessionId.value) } catch {}
  messages.value = []
  showHistory.value = false
  if (abortController) abortController.abort()
}

async function switchToSession(id) {
  if (id === sessionId.value) { showHistory.value = false; return }
  // 保存当前对话
  if (messages.value.length > 0) {
    saveHistory(sessionId.value, messages.value)
    const firstMsg = messages.value.find(m => m.role === 'user')
    addToHistory(sessionId.value, firstMsg?.content || '')
  }
  // 切换到目标会话
  sessionId.value = id
  try { localStorage.setItem('chat_session_id', sessionId.value) } catch {}
  messages.value = []
  loading.value = false
  if (abortController) abortController.abort()
  // 从后端加载目标会话的消息
  const msgs = await fetchHistory(id)
  if (msgs.length) messages.value = msgs
  showHistory.value = false
}

// ====== 消息状态 ======
const messages = ref([])
const loading = ref(false)
const pendingImage = ref('')

// 图片选择：压缩后转为 base64
function selectImage(file) {
  if (!file || loading.value) return
  const img = new Image()
  img.onload = () => {
    const canvas = document.createElement('canvas')
    let w = img.width, h = img.height
    const maxSize = 800
    if (w > maxSize || h > maxSize) {
      if (w > h) { h = h / w * maxSize; w = maxSize }
      else { w = w / h * maxSize; h = maxSize }
    }
    canvas.width = w; canvas.height = h
    const ctx = canvas.getContext('2d')
    ctx.drawImage(img, 0, 0, w, h)
    pendingImage.value = canvas.toDataURL('image/jpeg', 0.8).split(',')[1]
  }
  img.src = URL.createObjectURL(file)
}

function clearImage() { pendingImage.value = '' }

// 组件挂载时从后端加载历史
fetchHistory(sessionId.value).then(msgs => {
  if (msgs.length) messages.value = msgs
})

let abortController = null

async function handleSend(text) {
  if ((!text.trim() && !pendingImage.value) || loading.value) return

  const displayText = text.trim() || '[图片]'
  const msg = { role: 'user', content: displayText }
  if (pendingImage.value) msg.imgSrc = `data:image/jpeg;base64,${pendingImage.value}`
  messages.value.push(msg)
  loading.value = true

  if (abortController) abortController.abort()
  abortController = new AbortController()

  try {
    if (pendingImage.value) {
      // 有图片 → 视觉模型描述 → 主模型+工具综合回答
      const response = await doChatVision(text, abortController.signal, sessionId.value, pendingImage.value)
      pendingImage.value = ''
      let aiMsgIndex = -1
      let thinkSectionStart = -1
      await parseSseStream(response, {
        onThink(data) {
          if (thinkSectionStart < 0) {
            thinkSectionStart = messages.value.length
            messages.value.push({ role: 'think', content: data })
          } else {
            const m = messages.value[thinkSectionStart]
            if (m && m.role === 'think') m.content += data
          }
        },
        onThinkClear() { thinkSectionStart = -1; aiMsgIndex = -1 },
        onText(data) {
          thinkSectionStart = -1
          if (aiMsgIndex < 0) {
            messages.value.push({ role: 'assistant', content: data })
            aiMsgIndex = messages.value.length - 1
          } else {
            messages.value[aiMsgIndex].content += data
          }
        },
        onTool(data) {
          thinkSectionStart = -1
          messages.value.push({ role: 'tool', content: data })
        },
        onError(data) {
          thinkSectionStart = -1
          messages.value.push({ role: 'assistant', content: `错误: ${data}` })
        },
      })
    } else {
      // 纯文字 → 走正常智能体接口
      const response = await props.chatFn(text, abortController.signal, sessionId.value, '')
      let aiMsgIndex = -1
      let thinkSectionStart = -1  // 跟踪当前步骤的 think 消息起始位置

    await parseSseStream(response, {
      onThink(data) {
        // 流式思考 token：累积到当前 think 消息
        if (thinkSectionStart < 0) {
          thinkSectionStart = messages.value.length
          messages.value.push({ role: 'think', content: data })
        } else {
          const msg = messages.value[thinkSectionStart]
          if (msg && msg.role === 'think') {
            msg.content += data
          }
        }
      },
      onThinkClear() {
        // 不再删除思考内容，改为保留可折叠（只重置步骤标记）
        thinkSectionStart = -1
        aiMsgIndex = -1
      },
      onText(data) {
        thinkSectionStart = -1
        if (aiMsgIndex < 0) {
          messages.value.push({ role: 'assistant', content: data })
          aiMsgIndex = messages.value.length - 1
        } else {
          messages.value[aiMsgIndex].content += data
        }
      },
      onTool(data) {
        thinkSectionStart = -1  // 新步骤开始
        messages.value.push({ role: 'tool', content: data })
      },
      onFile(data) {
        const fileName = data.split('/').pop()
        messages.value.push({ role: 'file', content: data, fileName })
      },
      onError(data) {
        thinkSectionStart = -1
        messages.value.push({ role: 'assistant', content: `错误: ${data}` })
      },
    })
  }
  } catch (err) {
    if (err.name === 'AbortError') return
    messages.value.push({ role: 'assistant', content: `请求出错: ${err.message || '未知错误'}` })
  } finally {
    loading.value = false
    abortController = null
    // 恢复后的旧消息 + 本次新消息一并保存到后端
    saveHistory(sessionId.value, messages.value)
  }
}

/** 语音识别 - 浏览器原生 Web Speech API */
function handleMicStart() {
  if (loading.value) return

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SR) {
    alert('当前浏览器不支持语音识别，请使用 Chrome')
    return
  }

  const recognition = new SR()
  recognition.lang = 'zh-CN'
  recognition.continuous = false
  recognition.interimResults = false

  messages.value.push({ role: 'tool', content: '🎤 请说话...' })

  recognition.onresult = (event) => {
    const text = event.results[0][0].transcript
    if (text.trim()) handleSend(text)
  }
  recognition.onerror = () => {}
  recognition.onspeechend = () => recognition.stop()
  recognition.start()
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f0f2f5;
}
.chat-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.back-btn {
  font-size: 0.9rem;
  color: #6366f1;
  white-space: nowrap;
  padding: 6px 12px;
  border-radius: 8px;
  transition: background 0.15s;
}
.back-btn:hover { background: #eef2ff; }
.header-info { flex: 1; }
.header-info h1 { font-size: 1.15rem; font-weight: 600; color: #1f2937; }
.new-chat-btn {
  font-size: 0.8rem; color: #6366f1; background: none;
  border: 1px solid #6366f1; border-radius: 8px; padding: 5px 12px;
  cursor: pointer; white-space: nowrap; transition: all 0.15s;
}
.new-chat-btn:hover { background: #eef2ff; }
.new-chat-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.header-actions { display: flex; gap: 8px; align-items: center; }
.history-btn {
  font-size: 0.8rem; color: #6b7280; background: none;
  border: 1px solid #d1d5db; border-radius: 8px; padding: 5px 10px;
  cursor: pointer; white-space: nowrap; transition: all 0.15s;
}
.history-btn:hover { background: #f3f4f6; color: #374151; }
.history-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* 历史对话面板 */
.history-panel {
  background: #fff; border-bottom: 1px solid #e5e7eb;
  max-height: 240px; overflow-y: auto; padding: 8px 0;
}
.history-empty { text-align: center; color: #9ca3af; padding: 20px; font-size: 0.85rem; }
.history-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 24px; cursor: pointer; transition: background 0.1s;
}
.history-item:hover { background: #f9fafb; }
.history-item.active { background: #eef2ff; }
.history-preview { flex: 1; font-size: 0.85rem; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.history-time { font-size: 0.75rem; color: #9ca3af; white-space: nowrap; }
.history-del {
  font-size: 1rem; color: #d1d5db; background: none; border: none;
  cursor: pointer; padding: 0 4px; line-height: 1;
}
.history-del:hover { color: #ef4444; }
</style>
