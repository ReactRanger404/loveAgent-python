"""语音合成工具 - 对应 Java 的 SpeechSynthesisTool"""
import os
import logging

from langchain_core.tools import tool
from dashscope.audio.tts import SpeechSynthesizer
from config import settings
from config.constants import FILE_SAVE_DIR

logger = logging.getLogger(__name__)


@tool
def text_to_speech(text: str, file_name: str = "output.wav") -> str:
    """
    Convert text to speech and save as audio file.
    :param text: Text to convert to speech
    :param file_name: Output file name (e.g. output.wav)
    :return: Success or error message
    """
    try:
        if len(text) > 20000:
            return "错误：文本超过 20000 字限制"

        # 调用 DashScope TTS
        result = SpeechSynthesizer.call(
            model=settings.dashscope_tts_model,
            voice=settings.dashscope_tts_voice,
            text=text,
            api_key=settings.dashscope_api_key,
        )

        if result.status_code != 200:
            return f"语音合成失败: {result.message}"

        # 保存为文件
        output_dir = os.path.join(FILE_SAVE_DIR, "audio")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, file_name)

        with open(output_path, "wb") as f:
            f.write(result.output_audio)

        return f"语音合成成功，文件: {output_path}"
    except Exception as e:
        return f"语音合成失败: {e!s}"


speech_synthesis_tool = text_to_speech
