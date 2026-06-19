"""基于文件持久化的对话记忆 - 对应 Java 的 FileBasedChatMemory"""
import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class FileBasedChatMemory:
    """
    基于 JSON 文件持久化的对话记忆
    对应 Java: FileBasedChatMemory.java (原本用 Kryo 序列化，这里改用 JSON)
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _get_file_path(self, conversation_id: str) -> str:
        return os.path.join(self.base_dir, f"{conversation_id}.json")

    def add(self, conversation_id: str, role: str, content: str):
        """添加一条消息到对话历史"""
        messages = self.get(conversation_id)
        messages.append({"role": role, "content": content})
        file_path = self._get_file_path(conversation_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)

    def get(self, conversation_id: str) -> list[dict]:
        """获取对话历史"""
        file_path = self._get_file_path(conversation_id)
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("读取对话记录失败: %s", e)
                return []
        return []

    def clear(self, conversation_id: str):
        """清除对话历史"""
        file_path = self._get_file_path(conversation_id)
        if os.path.exists(file_path):
            os.remove(file_path)

    def get_recent(self, conversation_id: str, max_messages: int = 10) -> list[dict]:
        """获取最近的 N 条消息"""
        messages = self.get(conversation_id)
        return messages[-max_messages:]
