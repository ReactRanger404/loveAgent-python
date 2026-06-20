<template>
  <ChatPage
    title="🧠 领域智能体"
    placeholder="描述你的问题，我会查知识库、搜索、生成文件来帮你..."
    :show-mic="true"
    :chat-fn="doChat"
  />
</template>

<script setup>
import ChatPage from './ChatPage.vue'
import { doChat } from '../api/chat.js'
</script>
