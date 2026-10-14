import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from aiogram import Bot
from aiogram.types import InputProfilePhotoStatic, FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import MEMES_DIR
from . import database

logger = logging.getLogger(__name__)


def get_meme_images() -> List[Path]:
    """Memes papkasidagi barcha rasm fayllarini saralangan holda qaytaradi."""
    if not MEMES_DIR.exists() or not MEMES_DIR.is_dir():
        logger.warning("Memes papkasi topilmadi: %s", MEMES_DIR)
        return []

    valid_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    images = [p for p in MEMES_DIR.iterdir() if p.is_file() and p.suffix.lower() in valid_extensions]

    # Agar 1.jpg, 2.jpg kabi raqamli nomlar bo'lsa, son bo'yicha saralash
    def sort_key(p: Path):
        stem = p.stem
        if stem.isdigit():
            return (0, int(stem))
        return (1, stem.lower())

    images.sort(key=sort_key)
    return images


async def rotate_profile_photo(bot: Bot, force: bool = False) -> Optional[Path]:
    """
    Navbatdagi profil rasmini o'rnatadi.
    Agar bugun allaqachon almashtirilgan bo'lsa va force=False bo'lsa, o'tkazib yuboradi.
    """
    images = get_meme_images()
    if not images:
        logger.warning("Memes papkasida hech qanday rasm topilmadi!")
        return None

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    last_date = await database.get_state("last_avatar_date")

    if not force and last_date == today_str:
        logger.info("Bugun profil rasmi allaqachon yangilangan (%s). O'tkazib yuborildi.", today_str)
        return None

    # Oxirgi rasm indeksini olish
    last_index_str = await database.get_state("last_avatar_index", "-1")
    try:
        last_index = int(last_index_str)
    except ValueError:
        last_index = -1

    # Navbatdagi indeks (aylana bo'ylab)
    next_index = (last_index + 1) % len(images)
    next_image = images[next_index]

    try:
        logger.info(
            "Profil rasmi almashtirilmoqda: %s (indeks: %d / %d)",
            next_image.name, next_index + 1, len(images)
        )
        photo_input = InputProfilePhotoStatic(photo=FSInputFile(str(next_image)))
        success = await bot.set_my_profile_photo(photo=photo_input)
        if success:
            await database.set_state("last_avatar_index", str(next_index))
            await database.set_state("last_avatar_date", today_str)
            logger.info("Profil rasmi muvaffaqiyatli yangilandi: %s", next_image.name)
            return next_image
        else:
            logger.warning("Telegram set_my_profile_photo False qaytardi.")
    except Exception as e:
        logger.error("Profil rasmini almashtirishda xatolik yuz berdi: %s", e)

    return None


def setup_avatar_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Profil rasmini har kuni UTC 00:00 da almashtiruvchi job'ni yoqadi."""
    scheduler = AsyncIOScheduler(timezone=timezone.utc)
    scheduler.add_job(
        rotate_profile_photo,
        trigger="cron",
        hour=0,
        minute=0,
        args=[bot],
        id="daily_avatar_rotation",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Profil rasmi avtomatik ravishda har kuni 00:00 UTC da yangilanadi.")
    return scheduler
