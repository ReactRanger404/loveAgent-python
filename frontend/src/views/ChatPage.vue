<template>
  <div class="chat-page">
    <header class="chat-header">
      <router-link to="/" class="back-btn">← 返回</router-link>
      <div class="header-info">
        <h1>{{ title }}</h1>
      </div>
    </header>

    <ChatRoom
      :messages="messages"
      :loading="loading"
      :placeholder="placeholder"
      :show-mic="showMic"
      @send="handleSend"
      @mic-start="handleMicStart"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChatRoom from '../components/ChatRoom.vue'
import { parseSseStream } from '../utils/sse.js'

const props = defineProps({
  title: { type: String, required: true },
  placeholder: { type: String, default: '输入消息，按 Enter 发送...' },
  showMic: { type: Boolean, default: false },
  chatFn: { type: Function, required: true },
})

const messages = ref([])
const loading = ref(false)
const sessionId = ref('session_' + Math.random().toString(36).substring(2, 10))
let abortController = null

async function handleSend(text) {
  if (!text.trim() || loading.value) return

  messages.value.push({ role: 'user', content: text })
  loading.value = true

  if (abortController) abortController.abort()
  abortController = new AbortController()

  try {
    const response = await props.chatFn(text, abortController.signal, sessionId.value)

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
        // 仅清空当前步骤的 think 消息（不影响之前步骤的思考过程）
        if (thinkSectionStart >= 0) {
          messages.value.splice(thinkSectionStart)
          thinkSectionStart = -1
        }
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
  } catch (err) {
    if (err.name === 'AbortError') return
    messages.value.push({ role: 'assistant', content: `请求出错: ${err.message || '未知错误'}` })
  } finally {
    loading.value = false
    abortController = null
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
.header-info h1 { font-size: 1.15rem; font-weight: 600; color: #1f2937; }
</style>
