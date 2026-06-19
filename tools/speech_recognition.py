"""语音识别工具 - 使用 DashScope Recognition API"""
import os
import logging

from langchain_core.tools import tool
from dashscope.audio.asr import Recognition, RecognitionCallback
from config import settings

logger = logging.getLogger(__name__)


class _ASRCallback(RecognitionCallback):
    """ASR 回调，收集识别结果"""

    def __init__(self):
        self.text = ""
        self.error = ""

    def on_event(self, result):
        """收到识别结果"""
        try:
            if result.is_sentence_end():
                sentence = result.get_sentence()
                if sentence and hasattr(sentence, 'text') and sentence.text:
                    self.text += sentence.text
        except Exception as e:
            logger.warning("ASR event parse error: %s", e)

    def on_error(self, result):
        """识别出错"""
        self.error = str(result)
        logger.error("ASR error: %s", result)

    def on_complete(self):
        """识别完成"""
        pass

    def on_close(self):
        """连接关闭"""
        pass

    def on_open(self):
        """连接建立"""
        pass


@tool
def recognize_audio_file(file_path: str) -> str:
    """
    Recognize speech from an audio file and convert to text.
    :param file_path: Path to the audio file (wav/mp3/m4a/webm)
    :return: Recognized text
    """
    try:
        if not os.path.exists(file_path):
            return f"错误：音频文件不存在 - {file_path}"

        if os.path.getsize(file_path) == 0:
            return "错误：音频文件为空"

        # 根据文件扩展名确定格式
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        audio_format = ext if ext else 'wav'

        # 创建回调
        callback = _ASRCallback()

        # 创建识别器并调用
        recognizer = Recognition(
            model=settings.dashscope_asr_model,
            format=audio_format,
            sample_rate=16000,
            callback=callback,
        )

        # call() 会自动读取文件、建立 WebSocket、发送音频、等待结果
        result = recognizer.call(file_path)

        # 检查是否有文本结果
        if callback.text:
            return callback.text

        # 从返回的 result 中提取
        if hasattr(result, 'get_sentence'):
            sentence = result.get_sentence()
            if sentence and hasattr(sentence, 'text') and sentence.text:
                return sentence.text

        if callback.error:
            return f"识别失败: {callback.error}"

        return "未识别到语音内容"

    except Exception as e:
        logger.error("音频识别失败", exc_info=e)
        return f"音频识别失败: {e!s}"


speech_recognition_tool = recognize_audio_file
