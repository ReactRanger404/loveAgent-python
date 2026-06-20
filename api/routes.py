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

from fastapi import APIRouter, Query, Request
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

    @router.post("/chat")
    async def domain_chat(request: Request):
        """SSE 流式调用领域智能体，支持会话记忆 + 图片识别"""
        body = await request.json()
        message = body.get("message", "")
        session_id = body.get("session_id", "")
        image_base64 = body.get("image", "")

        async def event_generator():
            if not all_tools or not llm:
                yield {"event": "error", "data": "智能体未初始化"}
                yield {"event": "done", "data": ""}
                return
            if not message:
                yield {"event": "error", "data": "缺少消息"}
                yield {"event": "done", "data": ""}
                return
            if not session_id:
                yield {"event": "error", "data": "缺少 session_id"}
                yield {"event": "done", "data": ""}
                return

            # ① 获取/创建会话
            session = await session_manager.get_or_create(session_id, all_tools, llm)
            agent = session_manager.prepare_agent(session)

            # 带了图片 → 切换到视觉模型
            if image_base64:
                from langchain_core.messages import HumanMessage
                from langchain_openai import ChatOpenAI
                user_message = HumanMessage(content=[
                    {"type": "text", "text": message},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                ])
                agent.messages.append({"role": "user_multimodal", "content": user_message})
                # 临时切换到视觉模型
                original_llm = agent._llm
                agent._llm = ChatOpenAI(
                    model=settings.dashscope_vision_model,
                    api_key=settings.dashscope_api_key,
                    base_url=settings.dashscope_base_url,
                    temperature=0.7,
                )
            else:
                agent.messages.append({"role": "user", "content": message})

            # ② 流式运行（用完恢复原模型）
            original_llm = getattr(agent, '_llm', None)
            try:
                async for event in agent.run_stream(message):
                    yield {"data": json.dumps(event, ensure_ascii=False)}
            finally:
                if image_base64 and original_llm:
                    agent._llm = original_llm

            # ③ 滑动窗口 + 持久化
            session_manager.apply_sliding_window(session, llm)
            import asyncio
            asyncio.create_task(session_manager.background_save(session))
            yield {"event": "done", "data": ""}

        return EventSourceResponse(event_generator())

    # ==================== 图片识别（视觉描述 → 主模型综合回答） ====================

    @router.post("/chat/vision")
    async def vision_chat(request: Request):
        """图片识别：视觉模型先描述 → 主模型+工具基于描述给出完整回答"""
        body = await request.json()
        message = body.get("message", "")
        session_id = body.get("session_id", "")
        image_base64 = body.get("image", "")

        if not image_base64 or not session_id:
            return Response(content="缺少图片或 session_id", status_code=400)

        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        # ① 视觉模型描述图片
        vision_llm = ChatOpenAI(
            model=settings.dashscope_vision_model,
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            temperature=0.7,
        )
        vision_prompt = message or "请用中文详细描述这张图片的内容"
        vision_msg = HumanMessage(content=[
            {"type": "text", "text": vision_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
        ])
        description = (await vision_llm.ainvoke([vision_msg])).content or ""

        # ② 把图片描述注入主模型
        enriched_message = f"{message}\n\n【用户上传的图片描述】\n{description}"

        async def event_generator():
            if not all_tools or not llm:
                yield {"data": json.dumps({"type": "error", "content": "智能体未初始化"}, ensure_ascii=False)}
                yield {"data": json.dumps({"type": "done", "content": ""}, ensure_ascii=False)}
                return

            session = await session_manager.get_or_create(session_id, all_tools, llm)
            agent = session_manager.prepare_agent(session)
            agent.messages.append({"role": "user", "content": enriched_message})

            async for event in agent.run_stream(enriched_message):
                yield {"data": json.dumps(event, ensure_ascii=False)}

            session_manager.apply_sliding_window(session, llm)
            import asyncio
            asyncio.create_task(session_manager.background_save(session))
            yield {"data": json.dumps({"type": "done", "content": ""}, ensure_ascii=False)}

        return EventSourceResponse(event_generator())

    # ==================== 历史记录 ====================

    @router.get("/chat/history")
    async def chat_history(session_id: str = Query(...)):
        """获取前端显示用的聊天记录"""
        try:
            ui_msgs = await session_manager.get_ui_messages(session_id)
            return Response(
                content=json.dumps(ui_msgs, ensure_ascii=False),
                media_type="application/json",
            )
        except Exception as e:
            logger.error("获取历史记录失败: %s", e)
            return Response(content="[]", media_type="application/json")

    @router.put("/chat/history")
    async def save_chat_history(request: Request, session_id: str = Query(...)):
        """保存前端显示用的聊天记录"""
        try:
            body = await request.json()
            ui_msgs = body.get("messages", [])
            await session_manager.save_ui_messages(session_id, ui_msgs)
            return Response(content="ok")
        except Exception as e:
            logger.error("保存历史记录失败: %s", e)
            return Response(content="fail", status_code=500)

    @router.delete("/chat/history")
    async def delete_chat_history(session_id: str = Query(...)):
        """删除指定会话的全部数据"""
        try:
            await session_manager.delete_session(session_id)
            return Response(content="ok")
        except Exception as e:
            logger.error("删除历史记录失败: %s", e)
            return Response(content="fail", status_code=500)

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
