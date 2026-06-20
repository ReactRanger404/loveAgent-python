"""PostgreSQL 会话持久化 — 存储摘要 + 消息历史，支持 pgvector"""

import json
import logging

from config import settings

logger = logging.getLogger(__name__)


async def _get_pool():
    """获取连接池（延迟初始化）"""
    import asyncpg
    return await asyncpg.create_pool(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db,
        min_size=1,
        max_size=5,
    )


async def _init() -> None:
    """建表（幂等）"""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                summary TEXT DEFAULT '',
                messages TEXT DEFAULT '[]',
                ui_messages TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
    await pool.close()
    logger.info("PostgreSQL 会话表已就绪 (127.0.0.1:5433)")


async def _load(session_id: str) -> dict | None:
    """从数据库加载会话"""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT summary, messages, ui_messages FROM sessions WHERE session_id = $1",
            session_id
        )
    await pool.close()
    if row is None:
        return None
    return {
        "summary": row["summary"] or "",
        "messages": json.loads(row["messages"]) if row["messages"] else [],
        "ui_messages": json.loads(row["ui_messages"]) if row["ui_messages"] else [],
    }


async def _save(session_id: str, summary: str, messages: list, ui_messages: list | None = None) -> None:
    """保存/更新会话（UPSERT）"""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO sessions (session_id, summary, messages, ui_messages, updated_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (session_id) DO UPDATE SET
                summary = EXCLUDED.summary,
                messages = EXCLUDED.messages,
                ui_messages = COALESCE(EXCLUDED.ui_messages, sessions.ui_messages),
                updated_at = NOW()
        """, session_id, summary, json.dumps(messages, ensure_ascii=False),
            json.dumps(ui_messages, ensure_ascii=False) if ui_messages is not None else None)
    await pool.close()


async def _save_ui_messages(session_id: str, ui_messages: list) -> None:
    """仅更新前端显示用的消息列表"""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET ui_messages = $1, updated_at = NOW() WHERE session_id = $2",
            json.dumps(ui_messages, ensure_ascii=False), session_id
        )
    await pool.close()


async def _delete(session_id: str) -> None:
    """删除会话"""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM sessions WHERE session_id = $1", session_id)
    await pool.close()


class SessionStorage:
    """异步 PostgreSQL 会话存储"""

    @staticmethod
    async def init():
        await _init()

    @staticmethod
    async def load(session_id: str) -> dict | None:
        return await _load(session_id)

    @staticmethod
    async def save(session_id: str, summary: str, messages: list, ui_messages: list | None = None):
        await _save(session_id, summary, messages, ui_messages)

    @staticmethod
    async def save_ui_messages(session_id: str, ui_messages: list):
        await _save_ui_messages(session_id, ui_messages)

    @staticmethod
    async def load_ui_messages(session_id: str) -> list:
        data = await _load(session_id)
        return data.get("ui_messages", []) if data else []

    @staticmethod
    async def delete(session_id: str):
        await _delete(session_id)
