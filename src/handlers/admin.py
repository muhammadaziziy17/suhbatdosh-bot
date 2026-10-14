import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from ..config import ADMIN_IDS, DEEPSEEK_MODEL, GLM_API_KEY, GLM_FALLBACK_MODELS
from ..avatar_service import rotate_profile_photo, get_meme_images
from .. import database

logger = logging.getLogger(__name__)

admin_router = Router()


def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshiradi."""
    if not ADMIN_IDS:
        # Agar admin belgilanmagan bo'lsa, xavfsizlik uchun hech kimni to'g'ridan-to'g'ri o'tkazmaydi
        return False
    return user_id in ADMIN_IDS


@admin_router.message(Command("update_avatar"))
async def cmd_update_avatar(message: Message) -> None:
    """Profil rasmini majburiy tarzda darhol navbatdagisiga almashtirish (Adminlar uchun)."""
    user_id = message.from_user.id if message.from_user else 0
    if ADMIN_IDS and not is_admin(user_id):
        await message.reply("Kechirasiz, ushbu buyruq faqat bot adminlari uchun!")
        return

    await message.reply("Profil rasmi yangilanmoqda, kuting...")
    new_img = await rotate_profile_photo(message.bot, force=True)

    if new_img:
        last_index = await database.get_state("last_avatar_index", "0")
        images = get_meme_images()
        await message.reply(
            f"✅ Profil rasmi muvaffaqiyatli almashtirildi!\n"
            f"📸 Yangi rasm: `{new_img.name}`\n"
            f"🔢 Tartib: {int(last_index) + 1} / {len(images)}"
        )
    else:
        await message.reply("⚠️ Profil rasmini almashtirishda xatolik yoki Memes papkasida rasm topilmadi.")


@admin_router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Bot statistikasi va holatini ko'rish (Adminlar uchun)."""
    user_id = message.from_user.id if message.from_user else 0
    if ADMIN_IDS and not is_admin(user_id):
        await message.reply("Kechirasiz, ushbu buyruq faqat bot adminlari uchun!")
        return

    images = get_meme_images()
    last_idx = await database.get_state("last_avatar_index", "Noma'lum")
    last_date = await database.get_state("last_avatar_date", "Hali yangilanmagan")

    total_tokens = await database.get_total_chat_tokens(message.chat.id)
    api_usage = await database.get_deepseek_usage(message.chat.id)
    fallback_models = ", ".join(GLM_FALLBACK_MODELS) if GLM_API_KEY else "sozlanmagan"

    info_text = (
        "📊 **Legenda Suhbatdosh Bot Statistikasi**\n\n"
        f"🤖 **AI Model**: `{DEEPSEEK_MODEL}` (DeepSeek V4.1 Flash)\n"
        f"🛡 **Ixtiyoriy GLM zaxirasi**: `{fallback_models}`\n"
        f"🖼 **Memes rasmlar soni**: {len(images)} ta\n"
        f"📸 **Oxirgi profil rasm indeksi**: {last_idx}\n"
        f"📅 **Oxirgi rasm yangilangan sana**: {last_date}\n"
        f"📡 **DeepSeek API usage (shu chat)**: {api_usage['prompt_tokens']:,} input / "
        f"{api_usage['completion_tokens']:,} output / {api_usage['total_tokens']:,} jami token\n"
        f"💬 **Chat xotirasi**: ~{total_tokens:,} taxminiy token"
    )
    await message.reply(info_text, parse_mode="Markdown")
