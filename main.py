import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import TELEGRAM_BOT_TOKEN, DEEPSEEK_MODEL
from .database import init_db
from .avatar_service import rotate_profile_photo, setup_avatar_scheduler
from .handlers import main_router

# Logging sozlamalari
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("LegendaBot")


async def main() -> None:
    logger.info("Legenda Suhbatdosh boti ishga tushirilmoqda...")
    logger.info("AI provider: DeepSeek (%s)", DEEPSEEK_MODEL)

    # 1. Ma'lumotlar bazasini initsializatsiya qilish
    await init_db()

    # 2. Bot va Dispatcher obyektlarini yaratish
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # 3. Handlerlarni ulash
    dp.include_router(main_router)

    # Telegram menyusi uchun buyruqlarni sozlash
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="suhbat_boshlash", description="Suhbatni boshlash (Legenda qo'shiladi)"),
        BotCommand(command="stop_suhbatdosh", description="Suhbatni to'xtatish (Faqat chaqirilganda)"),
        BotCommand(command="clear", description="Guruh suhbat tarixini tozalash"),
        BotCommand(command="help", description="Yordam va qo'llanma")
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.warning("Bot buyruqlarini ro'yxatdan o'tkazishda xatolik: %s", e)

    # Bot ma'lumotlarini konsolga chiqarish
    bot_info = await bot.get_me()
    logger.info("Bot tayyor! Ismi: %s | Username: @%s", bot_info.first_name, bot_info.username)
    logger.info("Guruhlarda Privacy Mode o'chirilganligiga ishonch hosil qiling!")

    try:
        await rotate_profile_photo(bot, force=False)
    except Exception as e:
        logger.warning("Bot ishga tushganda profil rasmini yangilashda xatolik: %s", e)

    scheduler = setup_avatar_scheduler(bot)

    try:
        # Eski kutilayotgan yangilanishlarni tozalash va pollingni boshlash
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Bot to'xtatilmoqda...")
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Bot to'liq to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Dastur foydalanuvchi tomonidan to'xtatildi.")
