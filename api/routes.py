"""
FastAPI 路由 - 对应 Java 的 AiController.java

所有端点：
  GET  /api/ai/love_app/chat/sync           - 恋爱大师同步对话
  GET  /api/ai/love_app/chat/sse             - 恋爱大师 SSE 流式对话
  GET  /api/ai/manus/chat                    - Manus 智能体 SSE 流式对话
  GET  /api/ai/vision/chat                   - 多模态对话（图片 URL）
  POST /api/ai/vision/chat/upload            - 多模态对话（上传图片）
  POST /api/ai/asr/recognize                 - 语音识别
  GET  /api/ai/tts/synthesize                - 语音合成
"""
import json
import os
import tempfile
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, Response
from sse_starlette.sse import EventSourceResponse

from config import settings
from config.constants import FILE_SAVE_DIR
from tools.speech_recognition import recognize_audio_file
from tools.speech_synthesis import text_to_speech

logger = logging.getLogger(__name__)


def create_router(love_app, manus_agent, vision_llm):
    """
    创建路由函数（工厂模式，注入依赖）
    对应 Java: AiController 中的 @Resource 注入
    """
    router = APIRouter(prefix="/ai")

    # ==================== 恋爱大师 ====================

    @router.get("/love_app/chat/sync")
    def love_chat_sync(
        message: str = Query(...),
        chat_id: str = Query(default=""),
    ):
        """同步调用 AI 恋爱大师"""
        result = love_app.chat(message, chat_id or None)
        return Response(content=result, media_type="text/plain; charset=utf-8")

    @router.get("/love_app/chat/sse")
    async def love_chat_sse(
        message: str = Query(...),
        chat_id: str = Query(default=""),
    ):
        """SSE 流式调用 AI 恋爱大师"""
        async def event_generator():
            async for chunk in love_app.chat_stream(message, chat_id or None):
                yield {"data": chunk}
            yield {"data": "[DONE]"}

        return EventSourceResponse(event_generator())

    # ==================== Manus 超级智能体 ====================

    @router.get("/manus/chat")
    async def manus_chat(message: str = Query(...)):
        """SSE 流式调用 Manus 超级智能体"""
        async def event_generator():
            async for chunk in manus_agent.run_stream(message):
                yield {"data": chunk}
            yield {"data": "[DONE]"}

        return EventSourceResponse(event_generator())

    # ==================== 多模态对话 ====================

    @router.get("/vision/chat")
    async def vision_chat_url(
        message: str = Query(...),
        image_url: Optional[str] = Query(default=None),
    ):
        """多模态对话（通过图片 URL）"""
        async def event_generator():
            try:
                messages = [{"role": "user", "content": [{"type": "text", "text": message}]}]

                if image_url:
                    messages[0]["content"].append({
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    })

                response = vision_llm.invoke(messages)
                content = response.content if hasattr(response, "content") else str(response)
                yield {"data": content}
            except Exception as e:
                yield {"data": f"处理失败: {e!s}"}
            yield {"data": "[DONE]"}

        return EventSourceResponse(event_generator())

    @router.post("/vision/chat/upload")
    async def vision_chat_upload(
        message: str = Form(...),
        file: UploadFile = File(default=None),
    ):
        """多模态对话（上传图片文件）"""
        async def event_generator():
            try:
                messages = [{"role": "user", "content": [{"type": "text", "text": message}]}]

                if file and file.filename:
                    # 保存上传的文件到临时位置
                    temp_dir = tempfile.gettempdir()
                    temp_path = os.path.join(temp_dir, file.filename)
                    content = await file.read()
                    with open(temp_path, "wb") as f:
                        f.write(content)

                    # 将图片转为 base64 data URI
                    import base64
                    b64_data = base64.b64encode(content).decode("utf-8")
                    data_uri = f"data:{file.content_type or 'image/jpeg'};base64,{b64_data}"
                    messages[0]["content"].append({
                        "type": "image_url",
                        "image_url": {"url": data_uri},
                    })

                    # 清理临时文件
                    os.remove(temp_path)

                response = vision_llm.invoke(messages)
                content = response.content if hasattr(response, "content") else str(response)
                yield {"data": content}
            except Exception as e:
                yield {"data": f"处理失败: {e!s}"}
            yield {"data": "[DONE]"}

        return EventSourceResponse(event_generator())

    # ==================== 语音识别 ====================

    @router.post("/asr/recognize")
    async def asr_recognize(file: UploadFile = File(...)):
        """语音识别（上传音频文件，返回识别文字）"""
        if not file.filename:
            return Response(content="请上传音频文件", status_code=400)

        try:
            # 保存到临时文件
            temp_dir = os.path.join(FILE_SAVE_DIR, "temp_audio")
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, file.filename)
            content = await file.read()
            with open(temp_path, "wb") as f:
                f.write(content)

            # 调用语音识别
            result = recognize_audio_file.invoke({"file_path": temp_path})

            # 清理临时文件
            os.remove(temp_path)

            return Response(content=result, media_type="text/plain; charset=utf-8")
        except Exception as e:
            logger.error("语音识别失败", exc_info=e)
            return Response(content=f"语音识别失败: {e!s}", status_code=500)

    # ==================== 语音合成 ====================

    @router.get("/tts/synthesize")
    async def tts_synthesize(text: str = Query(...)):
        """语音合成（文字转语音，返回 WAV 音频流）"""
        try:
            import time
            temp_name = f"tts_temp_{int(time.time() * 1000)}.wav"

            result = text_to_speech.invoke({"text": text, "file_name": temp_name})

            if result.startswith("错误") or result.startswith("语音合成失败"):
                return Response(content=result, status_code=400)

            # 读取生成的音频文件
            audio_path = os.path.join(FILE_SAVE_DIR, "audio", temp_name)
            if not os.path.exists(audio_path):
                return Response(content="音频文件生成失败", status_code=500)

            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            # 删除临时文件
            os.remove(audio_path)

            return Response(
                content=audio_bytes,
                media_type="audio/wav",
                headers={"Content-Disposition": "inline"},
            )
        except Exception as e:
            logger.error("语音合成失败", exc_info=e)
            return Response(content=f"语音合成失败: {e!s}", status_code=500)

    return router
