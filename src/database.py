import aiosqlite
import logging
from typing import List, Dict, Optional, Any
from .config import DB_PATH

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Ma'lumotlar bazasi jadvallari va indekslarini yaratadi."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        # Bir vaqtda bir nechta yozish/o'qish bo'lganda qulflanib qolmasligi uchun WAL rejimi
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.execute("PRAGMA busy_timeout = 30000;")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER,
                sender_name TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_chat_id_id
            ON messages (chat_id, id);
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_summaries (
                chat_id INTEGER PRIMARY KEY,
                summary TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deepseek_usage (
                chat_id INTEGER PRIMARY KEY,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await db.commit()
    logger.info("SQLite ma'lumotlar bazasi tayyor: %s", DB_PATH)


async def add_message(
    chat_id: int,
    role: str,
    content: str,
    user_id: Optional[int] = None,
    sender_name: Optional[str] = None,
    token_count: int = 0
) -> int:
    """Yangi xabarni bazaga yozadi."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        cursor = await db.execute(
            """
            INSERT INTO messages (chat_id, user_id, sender_name, role, content, token_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, sender_name, role, content, token_count)
        )
        await db.commit()
        return cursor.lastrowid


async def get_recent_messages(chat_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    """Chatdagi oxirgi `limit` ta xabarni xronologik tartibda qaytaradi."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, role, sender_name, content, token_count, created_at
            FROM messages
            WHERE chat_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            # Xabarlarni qadimiydan yangisiga qarab tartiblaymiz
            messages = [dict(row) for row in reversed(rows)]
            return messages


async def get_total_chat_tokens(chat_id: int) -> int:
    """Chatdagi barcha saqlangan xabarlarning umumiy tokenlar sonini qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COALESCE(SUM(token_count), 0) FROM messages WHERE chat_id = ?",
            (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return int(row[0]) if row else 0


async def add_deepseek_usage(
    chat_id: int,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
) -> None:
    """DeepSeek API token sarfini chat bo'yicha jamlaydi."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        await db.execute(
            """
            INSERT INTO deepseek_usage (chat_id, prompt_tokens, completion_tokens, total_tokens)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                prompt_tokens = deepseek_usage.prompt_tokens + excluded.prompt_tokens,
                completion_tokens = deepseek_usage.completion_tokens + excluded.completion_tokens,
                total_tokens = deepseek_usage.total_tokens + excluded.total_tokens,
                updated_at = CURRENT_TIMESTAMP
            """,
            (chat_id, prompt_tokens, completion_tokens, total_tokens),
        )
        await db.commit()


async def get_deepseek_usage(chat_id: int) -> Dict[str, int]:
    """Chat uchun DeepSeek API'dan olingan haqiqiy token sarfini qaytaradi."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        async with db.execute(
            """
            SELECT prompt_tokens, completion_tokens, total_tokens
            FROM deepseek_usage
            WHERE chat_id = ?
            """,
            (chat_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "prompt_tokens": int(row[0]),
                    "completion_tokens": int(row[1]),
                    "total_tokens": int(row[2]),
                }
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


async def get_messages_for_summarization(chat_id: int, keep_last: int = 15) -> List[Dict[str, Any]]:
    """Xulosalash uchun eng eski xabarlarni oladi (oxirgi `keep_last` tasidan tashqari)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Eng yangi `keep_last` ta xabarning eng kichik ID sini topamiz
        async with db.execute(
            """
            SELECT id FROM messages
            WHERE chat_id = ?
            ORDER BY id DESC
            LIMIT 1 OFFSET ?
            """,
            (chat_id, keep_last - 1)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return []
            threshold_id = row["id"]

        # Undan eski barcha xabarlarni olamiz
        async with db.execute(
            """
            SELECT id, role, sender_name, content
            FROM messages
            WHERE chat_id = ? AND id < ?
            ORDER BY id ASC
            """,
            (chat_id, threshold_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def prune_old_messages(chat_id: int, keep_last: int = 15) -> None:
    """Xulosalangan eski xabarlarni o'chirib, faqat oxirgi `keep_last` tasini qoldiradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id FROM messages
            WHERE chat_id = ?
            ORDER BY id DESC
            LIMIT 1 OFFSET ?
            """,
            (chat_id, keep_last - 1)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return
            threshold_id = row["id"]

        await db.execute(
            "DELETE FROM messages WHERE chat_id = ? AND id < ?",
            (chat_id, threshold_id)
        )
        await db.commit()


async def get_chat_summary(chat_id: int) -> Optional[str]:
    """Chatning mavjud xulosasini qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT summary FROM chat_summaries WHERE chat_id = ?",
            (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def save_chat_summary(chat_id: int, summary: str) -> None:
    """Chat xulosasini yangilaydi yoki yaratadi."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO chat_summaries (chat_id, summary, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id) DO UPDATE SET
                summary = excluded.summary,
                updated_at = CURRENT_TIMESTAMP
            """,
            (chat_id, summary)
        )
        await db.commit()


async def clear_chat_history(chat_id: int) -> None:
    """Chat xotirasini va xulosasini tozalaydi."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        await db.execute("DELETE FROM chat_summaries WHERE chat_id = ?", (chat_id,))
        await db.commit()


async def get_state(key: str, default: Optional[str] = None) -> Optional[str]:
    """Bot holat qiymatini oladi."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM bot_state WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default


async def set_state(key: str, value: str) -> None:
    """Bot holat qiymatini saqlaydi."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO bot_state (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value)
        )
        await db.commit()


async def get_chat_state(chat_id: int, key: str, default: str = "") -> str:
    """Guruhga oid holat parametrini oladi."""
    val = await get_state(f"{chat_id}_{key}")
    return val if val is not None else default


async def set_chat_state(chat_id: int, key: str, value: str) -> None:
    """Guruhga oid holat parametrini saqlaydi."""
    await set_state(f"{chat_id}_{key}", str(value))


async def increment_chat_counter(chat_id: int) -> int:
    """Guruh xabarlar hisoblagichini 1 taga oshiradi va yangi qiymatni qaytaradi."""
    current_str = await get_chat_state(chat_id, "msg_count", "0")
    try:
        current = int(current_str)
    except ValueError:
        current = 0
    new_count = current + 1
    await set_chat_state(chat_id, "msg_count", str(new_count))
    return new_count
