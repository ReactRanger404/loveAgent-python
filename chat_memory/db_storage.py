"""SQLite 会话持久化 — 存储摘要 + 消息历史，服务器重启后 LLM 可恢复记忆"""

import json
import logging
import sqlite3
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 数据库文件存放在项目根目录
DB_DIR = Path(__file__).resolve().parent.parent / "tmp"
DB_PATH = DB_DIR / "sessions.db"


def _get_conn() -> sqlite3.Connection:
    """获取同步 SQLite 连接（每次调用都创建新连接，线程安全）"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # 提高并发性能
    return conn


def _init() -> None:
    """建表（幂等）"""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                summary TEXT DEFAULT '',
                messages TEXT DEFAULT '[]',
                ui_messages TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
    finally:
        conn.close()
    logger.info("会话数据库已就绪: %s", DB_PATH)


def _load(session_id: str) -> dict | None:
    """从数据库加载会话"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT summary, messages, ui_messages FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "summary": row["summary"] or "",
            "messages": json.loads(row["messages"]) if row["messages"] else [],
            "ui_messages": json.loads(row["ui_messages"]) if row["ui_messages"] else [],
        }
    finally:
        conn.close()


def _save(session_id: str, summary: str, messages: list, ui_messages: list | None = None) -> None:
    """保存/更新会话（UPSERT）"""
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO sessions (session_id, summary, messages, ui_messages, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(session_id) DO UPDATE SET
                summary = excluded.summary,
                messages = excluded.messages,
                ui_messages = COALESCE(excluded.ui_messages, sessions.ui_messages),
                updated_at = datetime('now')
        """, (
            session_id, summary, json.dumps(messages, ensure_ascii=False),
            json.dumps(ui_messages, ensure_ascii=False) if ui_messages is not None else None,
        ))
        conn.commit()
    finally:
        conn.close()


def _save_ui_messages(session_id: str, ui_messages: list) -> None:
    """仅更新前端显示用的消息列表"""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE sessions SET ui_messages = ?, updated_at = datetime('now') WHERE session_id = ?",
            (json.dumps(ui_messages, ensure_ascii=False), session_id)
        )
        conn.commit()
    finally:
        conn.close()


def _delete(session_id: str) -> None:
    """删除会话"""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()


class SessionStorage:
    """异步友好的会话存储封装"""

    @staticmethod
    async def init():
        """初始化数据库（应用启动时调用一次）"""
        import asyncio
        await asyncio.to_thread(_init)

    @staticmethod
    async def load(session_id: str) -> dict | None:
        """加载会话，返回 {summary, messages} 或 None"""
        import asyncio
        return await asyncio.to_thread(_load, session_id)

    @staticmethod
    async def save(session_id: str, summary: str, messages: list, ui_messages: list | None = None):
        """保存会话"""
        import asyncio
        await asyncio.to_thread(_save, session_id, summary, messages, ui_messages)

    @staticmethod
    async def save_ui_messages(session_id: str, ui_messages: list):
        """仅保存前端显示用的消息"""
        import asyncio
        await asyncio.to_thread(_save_ui_messages, session_id, ui_messages)

    @staticmethod
    async def load_ui_messages(session_id: str) -> list:
        """仅加载前端显示用的消息"""
        import asyncio
        data = await asyncio.to_thread(_load, session_id)
        return data.get("ui_messages", []) if data else []

    @staticmethod
    async def delete(session_id: str):
        """删除会话"""
        import asyncio
        await asyncio.to_thread(_delete, session_id)
