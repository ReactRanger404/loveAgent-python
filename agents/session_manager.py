"""会话管理器 — 滑动窗口记忆 + 摘要压缩 + DB 持久化 + 状态机复用"""

import asyncio
import logging
from typing import Optional

from agents.manus import Manus
from agents.agent_state import AgentState
from chat_memory.db_storage import SessionStorage

logger = logging.getLogger(__name__)

# 保留最近 N 轮对话（一轮 = 用户问 + AI 答）
MAX_ROUNDS = 10

# 摘要生成提示词 — 支持递归压缩（旧摘要会和新内容一起压缩）
SUMMARY_SYSTEM_PROMPT = "你是一个对话摘要助手。请将以下对话压缩为一段简洁的中文摘要，保留关键信息。"

SUMMARY_USER_PROMPT = """请将以下对话压缩为一段简洁的摘要（中文），保留：
- 用户关心的核心话题和问题
- AI 给出的关键建议
- 用户的态度或反馈

已有历史摘要：
{existing_summary}

新增对话内容：
{conversation}

要求：将已有摘要和新内容合并，压缩为一段通顺的摘要（200字以内），不要分点罗列："""

# 摘要最大字符数，超过时会递归压缩
MAX_SUMMARY_LENGTH = 500


class Session:
    """单个会话，包含 agent 实例和压缩摘要"""

    def __init__(self, session_id: str, agent: Manus):
        self.session_id = session_id
        self.agent = agent
        self.summary: str = ""  # 被压缩掉的旧轮次摘要
        self._save_task: Optional[asyncio.Task] = None


class SessionManager:
    """
    会话管理器

    职责：
    - 管理 agent 实例（复用而非每次新建）
    - 滑动窗口（只保留最近 MAX_ROUNDS 轮）
    - 摘要压缩（超出的轮次自动压缩）
    - 异步持久化（SQLite，重启后可恢复 LLM 记忆）
    """

    def __init__(self, persist: bool = True):
        self._sessions: dict[str, Session] = {}
        self._storage = SessionStorage() if persist else None

    async def get_or_create(self, session_id: str, all_tools=None, llm=None) -> Session:
        """获取或创建会话（优先从持久化存储恢复）"""
        if session_id not in self._sessions:
            agent = Manus(available_tools=all_tools, llm=llm) if all_tools and llm else None
            if not agent:
                raise RuntimeError("Agent 未初始化，请检查 LLM 和工具配置")
            self._sessions[session_id] = Session(session_id, agent)
            logger.info("创建新会话: %s", session_id)

            # 尝试从持久化存储恢复
            if self._storage:
                try:
                    saved = await self._storage.load(session_id)
                    if saved:
                        session = self._sessions[session_id]
                        session.summary = saved.get("summary", "")
                        if saved.get("messages"):
                            session.agent.messages = saved["messages"]
                        logger.info("会话 %s 已从数据库恢复 (%d 条消息)", session_id, len(saved.get("messages", [])))
                except Exception as e:
                    logger.warning("会话恢复失败（不影响使用）: %s", e)

        return self._sessions[session_id]

    def prepare_agent(self, session: Session) -> Manus:
        """
        准备 agent 接受新消息：
        - 如果已完成，重置状态
        - 注入摘要
        """
        agent = session.agent
        if agent.state != AgentState.IDLE:
            logger.info("Agent 状态 %s → 重置为 IDLE", agent.state)
            agent.reset()
        agent.summary = session.summary
        return agent

    def apply_sliding_window(self, session: Session, llm=None):
        """
        检查消息数量，如果超过 MAX_ROUNDS 轮则：
        1. 移除最早的多余轮次
        2. 异步生成摘要
        3. 保存到 session.summary
        """
        messages = session.agent.messages
        user_indices = [i for i, m in enumerate(messages) if m["role"] == "user"]

        if len(user_indices) <= MAX_ROUNDS:
            return  # 无需裁剪

        # 计算保留起始位置：保留最后 MAX_ROUNDS 条用户消息
        cutoff_idx = user_indices[-MAX_ROUNDS]
        old_messages = messages[:cutoff_idx]
        session.agent.messages = messages[cutoff_idx:]

        logger.info("滑动窗口裁剪：移除 %d 条消息，保留 %d 条",
                     len(old_messages), len(session.agent.messages))

        # 异步生成摘要（不阻塞当前请求）
        if llm and old_messages:
            session._save_task = asyncio.create_task(
                self._compress_summary(session, old_messages, llm)
            )

    async def _compress_summary(self, session: Session, old_messages: list[dict], llm):
        """
        将旧消息压缩为摘要（后台异步执行）
        支持递归压缩：已有摘要 + 新内容 → 重新压缩，防止无限膨胀
        """
        try:
            # 拼接待压缩的对话文本
            lines = []
            for m in old_messages:
                role = {"user": "用户", "assistant": "AI", "tool": "[工具]"}.get(m["role"], "其他")
                content = m.get("content", "")
                if m["role"] == "tool":
                    content = content[:80]
                lines.append(f"{role}: {content}")

            conversation_text = "\n".join(lines)

            if len(conversation_text) < 20 and not session.summary:
                return  # 内容太少且无旧摘要，跳过

            from langchain_core.messages import SystemMessage, HumanMessage
            response = await llm.ainvoke([
                SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
                HumanMessage(content=SUMMARY_USER_PROMPT.format(
                    existing_summary=session.summary or "无",
                    conversation=conversation_text,
                )),
            ])
            summary = response.content.strip() if hasattr(response, "content") else str(response).strip()
            if summary:
                session.summary = summary  # 直接替换，不再追加
                logger.info("会话 %s 摘要已更新 (%d 字符): %s...",
                            session.session_id, len(summary), summary[:60])
        except Exception as e:
            logger.warning("摘要生成失败（不影响对话）: %s", e)

    async def background_save(self, session: Session):
        """异步持久化会话（摘要 + 最近消息）到 SQLite"""
        try:
            # 等待正在进行的摘要任务完成
            if session._save_task:
                await session._save_task
                session._save_task = None

            if self._storage:
                # 只保存最近 N 轮消息 + 摘要，节省存储空间
                messages_to_save = session.agent.messages
                await self._storage.save(
                    session_id=session.session_id,
                    summary=session.summary,
                    messages=messages_to_save,
                )
                logger.debug("会话 %s 已持久化 (%d 条消息)", session.session_id, len(messages_to_save))
        except Exception as e:
            logger.error("会话持久化失败: %s", e)

    async def get_ui_messages(self, session_id: str) -> list:
        """获取前端显示用的聊天记录"""
        if not self._storage:
            return []
        try:
            return await self._storage.load_ui_messages(session_id)
        except Exception as e:
            logger.warning("读取 UI 消息失败: %s", e)
            return []

    async def save_ui_messages(self, session_id: str, ui_messages: list):
        """保存前端显示用的聊天记录"""
        if not self._storage:
            return
        try:
            await self._storage.save_ui_messages(session_id, ui_messages)
        except Exception as e:
            logger.warning("保存 UI 消息失败: %s", e)

    async def delete_session(self, session_id: str):
        """删除会话数据（内存 + 数据库）"""
        self.remove_session(session_id)
        if self._storage:
            try:
                await self._storage.delete(session_id)
                logger.info("会话 %s 已从数据库删除", session_id)
            except Exception as e:
                logger.warning("删除数据库记录失败: %s", e)

    def remove_session(self, session_id: str):
        """清理会话（用户主动退出或超时）"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("会话已清理: %s", session_id)

    @property
    def active_count(self) -> int:
        """当前活跃会话数"""
        return len(self._sessions)
