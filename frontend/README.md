# AI Agent 前端

基于 Vue 3 + Vite + Axios 的 AI 应用前端项目。

## 功能

- **主页**：应用切换入口
- **AI 恋爱大师**：聊天室风格，SSE 流式对话，自动生成会话 ID
- **AI 超级智能体**：聊天室风格，SSE 流式对话

## 启动

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:5173

## 后端接口

开发环境通过 Vite 代理转发到 `http://localhost:8123/api`：

| 应用 | 接口 |
|------|------|
| AI 恋爱大师 | `GET /api/ai/love_app/chat/sse?message=&chatId=` |
| AI 超级智能体 | `GET /api/ai/manus/chat?message=` |

## 项目结构

```
src/
├── api/          # 接口封装（axios + SSE fetch）
├── components/   # 公共组件
├── router/       # 路由
├── styles/       # 全局样式
├── utils/        # 工具函数
└── views/        # 页面
```
