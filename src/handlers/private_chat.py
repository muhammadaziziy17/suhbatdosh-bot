import logging
from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from ..config import TELEGRAM_BOT_USERNAME

logger = logging.getLogger(__name__)

private_router = Router()
# Faqat shaxsiy chatdagi xabarlarni filtrlash
private_router.message.filter(F.chat.type == ChatType.PRIVATE)


@private_router.message()
async def handle_private_message(message: Message) -> None:
    """
    Shaxsiy chatda kelgan barcha xabarlar va buyruqlarga javob.
    Foydalanuvchiga bot faqat guruhlarda ishlashini ma'lum qiladi va guruhga qo'shish tugmasini taklif etadi.
    """
    bot_username = TELEGRAM_BOT_USERNAME.lstrip("@")
    add_to_group_url = f"https://t.me/{bot_username}?startgroup=true" if bot_username else "https://t.me/"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Meni guruhga qo'shish",
                    url=add_to_group_url
                )
            ]
        ]
    )

    text = (
        "Salom, hurmatli do'stim! 😎\n\n"
        "Men — **Legenda Suhbatdosh**man. Men shaxsiy chatlarda emas, "
        "**faqat guruhlarda** do'stlaringiz bilan qiziqarli, xushchaqchaq va erkin suhbat qurish uchun yaratilganman.\n\n"
        "Meni o'z guruhingizga qo'shing va birgalikda muloqot qilamiz! Pastdagi tugmani bosing 👇"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
