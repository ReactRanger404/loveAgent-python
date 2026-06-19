# AI Agent - Python 版

这是从 Java（Spring AI）重构到 Python（FastAPI + LangChain）的 AI 智能体项目。

## 项目结构

```
ai-agent-python/
├── app.py                  # FastAPI 应用入口
├── config/                 # 配置管理
│   ├── settings.py         # Pydantic Settings（环境变量）
│   └── constants.py        # 文件目录常量
├── api/
│   └── routes.py           # FastAPI 路由（SSE 流式接口）
├── agents/                 # 智能体系统
│   ├── agent_state.py      # AgentState 枚举
│   ├── base_agent.py       # BaseAgent 抽象基类
│   ├── react_agent.py      # ReAct（思考-行动）模式
│   ├── tool_agent.py       # 工具调用智能体
│   └── manus.py            # Manus 超级智能体
├── advisors/               # 请求/响应增强器
│   ├── logger_advisor.py   # 日志记录
│   └── rereread_advisor.py # Re2 重读增强
├── apps/
│   └── love_app.py         # 恋爱大师应用（RAG + 记忆）
├── chat_memory/
│   └── file_based_memory.py # 基于文件的对话记忆
├── rag/                    # RAG 增强检索
│   ├── document_loader.py  # 文档加载
│   ├── vector_store.py     # 向量存储配置
│   ├── text_splitter.py    # 文本切分
│   ├── keyword_enricher.py # AI 关键词增强
│   ├── query_rewriter.py   # 查询重写
│   └── query_augmenter.py  # 查询增强
├── tools/                  # AI 工具
│   ├── __init__.py         # 工具注册
│   ├── file_operation.py   # 文件读写
│   ├── web_search.py       # 百度搜索
│   ├── web_scraping.py     # 网页抓取
│   ├── resource_download.py# 资源下载
│   ├── terminal_operation.py# 终端命令
│   ├── pdf_generation.py   # PDF 生成
│   ├── speech_recognition.py # 语音识别
│   ├── speech_synthesis.py # 语音合成
│   ├── image_search.py     # 图片搜索
│   └── terminate.py        # 终止工具
├── documents/              # RAG 知识库文档
├── tmp/file/               # 文件保存目录
└── .env                    # 环境变量（API Key 等）
```

## 快速开始

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 填写你的 API Key
```

3. 启动服务
```bash
python app.py
# 服务运行在 http://localhost:8123/api
```

## 对比 Java 版本

| 维度 | Java 版 | Python 版 |
|------|---------|-----------|
| Web 框架 | Spring Boot 3.4 | FastAPI |
| LLM 框架 | Spring AI 1.0 | LangChain |
| AI 模型 | 阿里云 DashScope | 阿里云 DashScope |
| 向量存储 | PGVector / SimpleVectorStore | ChromaDB |
| 代码风格 | 注解驱动 + Lombok | Pydantic + 装饰器 |
| 异步 | Reactor + WebFlux | asyncio + SSE |
