"""语音识别工具 - 对应 Java 的 SpeechRecognitionTool"""
import os
import logging

from langchain_core.tools import tool
from dashscope.audio.asr import Recognition
from config import settings

logger = logging.getLogger(__name__)


@tool
def recognize_audio_file(file_path: str) -> str:
    """
    Recognize speech from an audio file and convert to text.
    :param file_path: Path to the audio file (wav/mp3/m4a)
    :return: Recognized text
    """
    try:
        if not os.path.exists(file_path):
            return f"错误：音频文件不存在 - {file_path}"

        # 调用 DashScope Paraformer 识别
        recognition = Recognition(
            model=settings.dashscope_asr_model,
            api_key=settings.dashscope_api_key,
            format="wav",
            sample_rate=16000,
        )
        result = recognition.call(file_path)
        if result.status_code == 200:
            # 解析识别结果
            text_parts = []
            for sentence in result.output.sentence_list:
                text_parts.append(sentence.text)
            return "".join(text_parts)
        else:
            return f"识别失败: {result.message}"
    except Exception as e:
        return f"音频识别失败: {e!s}"


speech_recognition_tool = recognize_audio_file
