<template>
  <div class="chat-room">
    <div ref="messageListRef" class="message-list">
      <div v-if="groupedMessages.length === 0" class="empty-tip">
        <p>{{ emptyText }}</p>
      </div>

      <template v-for="(item, idx) in groupedMessages" :key="idx">
        <!-- 思考过程（流式显示，始终可见） -->
        <div v-if="item.type === 'think-group'" class="think-area">
          <div class="think-header">🤔 思考过程</div>
          <div class="think-steps">
            <div v-for="(t, ti) in item.steps" :key="ti" class="think-step" :class="t.role">
              <template v-if="t.role === 'think'">💭 {{ t.content }}</template>
              <template v-else-if="t.role === 'tool'"><span class="tool-call">🔧 {{ t.content }}</span></template>
            </div>
            <div v-if="loading && isLastThinkGroup(idx)" class="think-step thinking-dots">
              <span>思考中</span><i></i><i></i><i></i>
            </div>
          </div>
        </div>

        <!-- 用户/AI 消息 -->
        <div v-else-if="item.type === 'message'" class="message-row" :class="item.msg.role">
          <template v-if="item.msg.role === 'user' || item.msg.role === 'assistant'">
            <div class="avatar">{{ item.msg.role === 'user' ? '我' : 'AI' }}</div>
            <div class="bubble-wrapper">
              <div class="bubble">
                <span v-if="item.msg.content">{{ item.msg.content }}</span>
                <span v-else-if="loading && item.msg.role === 'assistant' && idx === lastAssistantIdx" class="typing">
                  <i></i><i></i><i></i>
                </span>
              </div>
              <button
                v-if="item.msg.role === 'assistant' && item.msg.content && !loading"
                class="tts-btn" title="播放语音" @click="playTts(item.msg.content)"
              >🔊</button>
            </div>
          </template>
        </div>

        <!-- 文件下载 -->
        <div v-else-if="item.type === 'file'" class="file-download">
          <a :href="item.msg.content" target="_blank" class="download-link">
            📄 {{ item.msg.fileName || '下载文件' }}
          </a>
        </div>
      </template>
    </div>

    <div class="input-area">
      <button v-if="showMic" class="mic-btn" :disabled="loading" title="语音输入" @click="$emit('mic-start')">🎤</button>
      <textarea v-model="inputText" :placeholder="placeholder" :disabled="loading" rows="1"
        @keydown.enter.exact.prevent="send" />
      <button class="send-btn" :disabled="loading || !inputText.trim()" @click="send">
        {{ loading ? '思考中...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  placeholder: { type: String, default: '输入消息...' },
  emptyText: { type: String, default: '开始对话吧，AI 随时为你服务' },
  showMic: { type: Boolean, default: false },
})

const emit = defineEmits(['send', 'mic-start'])

const inputText = ref('')
const messageListRef = ref(null)

/** 把 think/tool 合并为思考组，消息和文件单独 */
const groupedMessages = computed(() => {
  const result = []
  let currentThink = null

  for (const msg of props.messages) {
    if (msg.role === 'think' || msg.role === 'tool') {
      if (!currentThink) {
        currentThink = { type: 'think-group', steps: [] }
        result.push(currentThink)
      }
      currentThink.steps.push({ role: msg.role, content: msg.content })
    } else {
      currentThink = null
      if (msg.role === 'file') {
        result.push({ type: 'file', msg })
      } else {
        result.push({ type: 'message', msg })
      }
    }
  }
  return result
})

/** 判断是否是最后一个思考组（用于显示"思考中"动画） */
function isLastThinkGroup(idx) {
  for (let i = idx + 1; i < groupedMessages.value.length; i++) {
    if (groupedMessages.value[i].type !== 'think-group') return false
  }
  return true
}

/** 最后一个 assistant 消息索引 */
const lastAssistantIdx = computed(() => {
  const items = groupedMessages.value
  for (let i = items.length - 1; i >= 0; i--) {
    if (items[i].type === 'message' && items[i].msg.role === 'assistant') return i
  }
  return -1
})

function send() {
  const text = inputText.value.trim()
  if (!text || props.loading) return
  emit('send', text)
  inputText.value = ''
}

function playTts(text) {
  if (!text) return
  const encoded = encodeURIComponent(text.slice(0, 500))
  const audio = new Audio(`/api/tts/synthesize?text=${encoded}`)
  audio.play().catch(() => {})
}

watch(() => props.messages, async () => {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}, { deep: true })
</script>

<style scoped>
.chat-room { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.message-list { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 12px; }
.empty-tip { display: flex; align-items: center; justify-content: center; height: 100%; color: #9ca3af; font-size: 0.95rem; }

/* ===== 思考过程（流式显示） ===== */
.think-area {
  background: #f8f8ff;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 12px 16px;
  max-width: 90%;
  align-self: flex-start;
}
.think-header {
  font-size: 0.8rem;
  font-weight: 600;
  color: #888;
  margin-bottom: 8px;
}
.think-steps {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.think-step {
  font-size: 0.8rem;
  line-height: 1.7;
  padding: 1px 0;
}
.think-step.think {
  color: #7c3aed;
  font-style: italic;
}
.tool-call {
  color: #aaa;
  font-style: normal;
}

.thinking-dots { display: flex; align-items: center; gap: 2px; margin-top: 4px; }
.thinking-dots span { font-size: 0.75rem; color: #aaa; }
.thinking-dots i {
  width: 4px; height: 4px; border-radius: 50%;
  background: #bbb; animation: bounce 1.2s infinite ease-in-out;
}
.thinking-dots i:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots i:nth-child(3) { animation-delay: 0.4s; }

/* ===== 消息 ===== */
.message-row { display: flex; align-items: flex-start; gap: 10px; max-width: 78%; }
.message-row.user { flex-direction: row-reverse; align-self: flex-end; }
.message-row.assistant { align-self: flex-start; }
.avatar {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 600; flex-shrink: 0;
}
.message-row.user .avatar { background: #6366f1; color: #fff; }
.message-row.assistant .avatar { background: #e5e7eb; color: #374151; }
.bubble-wrapper { display: flex; align-items: flex-start; gap: 6px; }
.bubble {
  padding: 10px 14px; border-radius: 12px;
  font-size: 0.95rem; line-height: 1.6;
  word-break: break-word; white-space: pre-wrap;
}
.message-row.user .bubble { background: #6366f1; color: #fff; border-bottom-right-radius: 4px; }
.message-row.assistant .bubble { background: #fff; color: #1f2937; border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.tts-btn {
  background: none; border: 1px solid #e5e7eb; border-radius: 8px; padding: 4px 8px;
  cursor: pointer; font-size: 0.9rem; opacity: 0.6; transition: opacity 0.15s; margin-top: 4px; flex-shrink: 0;
}
.tts-btn:hover { opacity: 1; background: #f3f4f6; }

/* ===== 文件下载 ===== */
.file-download { align-self: center; }
.download-link {
  display: inline-block; padding: 8px 16px; background: #eef2ff;
  color: #4f46e5; border-radius: 8px; text-decoration: none; font-size: 0.9rem; font-weight: 500;
}
.download-link:hover { background: #e0e7ff; }

/* ===== 动画 ===== */
.typing { display: inline-flex; gap: 4px; align-items: center; height: 20px; }
.typing i { width: 6px; height: 6px; border-radius: 50%; background: #9ca3af; animation: bounce 1.2s infinite ease-in-out; }
.typing i:nth-child(2) { animation-delay: 0.2s; }
.typing i:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,80%,100% { transform: scale(0.6); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }

/* ===== 输入区 ===== */
.input-area { display: flex; align-items: center; gap: 10px; padding: 16px 24px; background: #fff; border-top: 1px solid #e5e7eb; }
.mic-btn {
  background: none; border: 1px solid #d1d5db; border-radius: 50%; width: 40px; height: 40px;
  font-size: 1.1rem; cursor: pointer; flex-shrink: 0; transition: all 0.15s;
}
.mic-btn:hover:not(:disabled) { background: #eef2ff; border-color: #6366f1; }
.mic-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.input-area textarea {
  flex: 1; resize: none; border: 1px solid #d1d5db; border-radius: 12px; padding: 10px 14px;
  font-size: 0.95rem; line-height: 1.5; outline: none; max-height: 120px; transition: border-color 0.15s;
}
.input-area textarea:focus { border-color: #6366f1; }
.input-area textarea:disabled { background: #f9fafb; cursor: not-allowed; }
.send-btn {
  padding: 10px 20px; background: #6366f1; color: #fff; border: none; border-radius: 12px;
  font-size: 0.95rem; font-weight: 500; cursor: pointer; white-space: nowrap; transition: background 0.15s;
}
.send-btn:hover:not(:disabled) { background: #4f46e5; }
.send-btn:disabled { background: #c7d2fe; cursor: not-allowed; }
</style>
