<template>
  <div class="home">
    <header class="home-header">
      <h1>领域智能体</h1>
      <p>知识库 + 工具调用 = 真正的 AI 领域专家</p>
    </header>

    <main class="app-grid">
      <router-link to="/chat" class="app-card">
        <div class="card-icon">🧠</div>
        <h2>开始对话</h2>
        <p>结合恋爱知识库、联网搜索、文件处理等能力，一站式解决你的问题。</p>
        <span class="card-action">进入 →</span>
      </router-link>
    </main>

    <footer class="home-footer">
      <p>支持：语音输入 🎤 · 语音播放 🔊 · PDF 生成 📄 · 联网搜索 🌐 · 知识库 📚</p>
    </footer>
  </div>
</template>

<style scoped>
.home {
  min-height: 100vh;
  padding: 48px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
}
.home-header {
  text-align: center;
  color: #fff;
  margin-bottom: 48px;
}
.home-header h1 { font-size: 2.25rem; font-weight: 700; margin-bottom: 12px; }
.home-header p { font-size: 1.05rem; opacity: 0.9; }
.app-grid { width: 100%; max-width: 400px; }
.app-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px 32px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
}
.app-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}
.card-icon { font-size: 3rem; }
.app-card h2 { font-size: 1.5rem; font-weight: 600; color: #1f2937; }
.app-card p { font-size: 0.95rem; color: #6b7280; line-height: 1.6; }
.card-action { font-size: 1rem; font-weight: 600; color: #8b5cf6; }
.home-footer { margin-top: 48px; color: rgba(255,255,255,0.7); font-size: 0.85rem; }
</style>
