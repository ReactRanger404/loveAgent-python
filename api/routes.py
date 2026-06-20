"""
FastAPI 路由 - 合并后的领域智能体

端点：
  GET  /api/chat                          - 领域智能体 SSE 流式对话（滑动窗口记忆 + async 持久化）
  GET  /api/file/{path}                   - 文件下载
  GET  /api/tts/synthesize                - 语音合成
"""
import json
import os
import logging
from urllib.parse import quote

from fastapi import APIRouter, Query
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from config import settings
from config.constants import FILE_SAVE_DIR
from agents.session_manager import SessionManager

logger = logging.getLogger(__name__)

# 全局会话管理器（agent 复用 + 滑动窗口 + 摘要压缩）
session_manager = SessionManager()


def create_router(all_tools=None, llm=None):
    """创建路由"""
    router = APIRouter()

    # ==================== 领域智能体 ====================

    @router.get("/chat")
    async def domain_chat(message: str = Query(...), session_id: str = Query(default="")):
        """SSE 流式调用领域智能体，支持会话记忆"""
        async def event_generator():
            if not all_tools or not llm:
                yield {"event": "error", "data": "智能体未初始化"}
                yield {"event": "done", "data": ""}
                return
            if not session_id:
                yield {"event": "error", "data": "缺少 session_id"}
                yield {"event": "done", "data": ""}
                return

            # ① 获取/创建会话（复用 agent 实例）
            session = session_manager.get_or_create(session_id, all_tools, llm)

            # ② 重置状态 + 注入摘要
            agent = session_manager.prepare_agent(session)

            # ③ 流式运行,async for 异步非阻塞循环
            async for event in agent.run_stream(message):
                yield {"data": json.dumps(event, ensure_ascii=False)}

            # ④ 滑动窗口裁剪（旧轮次移除 + 后台生成摘要）
            session_manager.apply_sliding_window(session, llm)

            # ⑤ 异步持久化（不阻塞响应）
            import asyncio
            asyncio.create_task(session_manager.background_save(session))

            yield {"event": "done", "data": ""}

        return EventSourceResponse(event_generator())

    # ==================== 文件下载 ====================

    @router.get("/file/{file_path:path}")
    async def serve_file(file_path: str):
        """提供生成的文件下载（PDF 等）"""
        full_path = os.path.join(FILE_SAVE_DIR, file_path)
        if not os.path.exists(full_path):
            return Response(content="文件不存在", status_code=404)

        raw_filename = os.path.basename(file_path)
        # 对中文文件名做 RFC 5987 编码，避免非 ASCII 字符导致响应头异常
        encoded_filename = quote(raw_filename, encoding='utf-8')
        disposition = f'inline; filename="{encoded_filename}"; filename*=UTF-8\'\'{encoded_filename}'

        content_type = "application/pdf" if file_path.endswith(".pdf") else "application/octet-stream"
        with open(full_path, "rb") as f:
            return Response(content=f.read(), media_type=content_type,
                            headers={"Content-Disposition": disposition})

    # ==================== 语音合成 ====================

    @router.get("/tts/synthesize")
    async def tts_synthesize(text: str = Query(...)):
        """语音合成（文字转语音，返回 WAV 音频流）"""
        from tools.speech_synthesis import text_to_speech
        try:
            import time
            temp_name = f"tts_temp_{int(time.time() * 1000)}.wav"
            result = text_to_speech.invoke({"text": text, "file_name": temp_name})

            if "失败" in result:
                return Response(content=result, status_code=400)

            audio_path = os.path.join(FILE_SAVE_DIR, "audio", temp_name)
            if not os.path.exists(audio_path):
                return Response(content="音频文件生成失败", status_code=500)

            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            os.remove(audio_path)

            return Response(content=audio_bytes, media_type="audio/wav",
                            headers={"Content-Disposition": "inline"})
        except Exception as e:
            logger.error("语音合成失败", exc_info=e)
            return Response(content=f"语音合成失败: {e!s}", status_code=500)

    return router
