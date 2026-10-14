import logging
from aiogram import Router, F
from aiogram.enums import ChatType, ChatAction
from aiogram.filters import Command
from aiogram.types import Message
from .. import database
from .. import ai_service

logger = logging.getLogger(__name__)

group_router = Router()
# Faqat guruh va superguruh xabarlarini qabul qilish
group_router.message.filter(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))


def split_text(text: str, chunk_size: int = 4000) -> list[str]:
    """Xabar 4000 belgidan oshsa, uni xavfsiz qismlarga bo'ladi."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    current_chunk = []
    current_len = 0

    lines = text.split("\n")
    for line in lines:
        if current_len + len(line) + 1 > chunk_size:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_len = len(line) + 1
        else:
            current_chunk.append(line)
            current_len += len(line) + 1

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


@group_router.message(Command("start"))
async def cmd_group_start(message: Message) -> None:
    """Guruhda /start buyrug'iga javob."""
    await message.reply(
        "Salom guruh ahli! 😎\n"
        "Men — **Legenda Suhbatdosh**man!\n\n"
        "Muloqot qilish tartibi:\n"
        "• `/suhbat_boshlash` — suhbatni faollashtirish (men gap boshlayman va qizg'in gaplashamiz)\n"
        "• `/stop_suhbatdosh` — suhbatni to'xtatish (faqat chaqirganingizda javob beraman)\n"
        "• Xabarlarimga **Reply** qilsangiz yoki @ atmetka qilsangiz doim javob beraman!",
        parse_mode="Markdown"
    )


@group_router.message(Command("help"))
async def cmd_group_help(message: Message) -> None:
    """Guruhda /help buyrug'i."""
    help_text = (
        "💡 **Legenda Suhbatdosh Guruh Qo'llanmasi**:\n\n"
        "• `/suhbat_boshlash` (yoki `/suhbat-boshlash`) — suhbatni boshlash\n"
        "• `/stop_suhbatdosh` (yoki `/stop-suhbatdosh`) — suhbatni to'xtatish\n"
        "• `/clear` — guruhdagi eski suhbat tarixini tozalash\n"
        "• Bot har doim atmetka qilinganda yoki uning xabariga **Reply** qilinganda javob beradi.\n"
        "• Suhbat rejimida bot umumiy mavzularga ham ora-orada (10 tadan 2 tasiga) qo'shilib turadi."
    )
    await message.reply(help_text, parse_mode="Markdown")


@group_router.message(Command("clear"))
async def cmd_group_clear(message: Message) -> None:
    """Guruh xotirasini tozalash."""
    await database.clear_chat_history(message.chat.id)
    await message.reply("🧹 Guruhdagi suhbat tarixi va xotira tozalandi! Yangi mavzudan boshlaymiz 😎")


@group_router.message(Command("suhbat_boshlash", "suhbat"))
@group_router.message(F.text.lower().startswith("/suhbat-boshlash") | F.text.lower().startswith("/suhbat_boshlash"))
async def cmd_start_chat(message: Message) -> None:
    """Suhbatni boshlash buyrug'i: suhbat rejimini yoqadi va bot o'zi gap boshlaydi."""
    chat_id = message.chat.id
    await database.set_chat_state(chat_id, "active_mode", "1")

    # Bot qiziqarli gap boshlashi uchun AI prompt
    starter_prompt = [
        {"role": "system", "content": ai_service.SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "Guruhda /suhbat_boshlash buyrug'i berildi. Guruh a'zolarini suhbatga chorlaydigan, biroz hazilkash, zamonaviy va 'legenda' uslubingizga mos 1-2 jumlali qiziqarli savol yoki fikr bilan gap boshlang."
        }
    ]

    starter_text = await ai_service.request_ai_response(starter_prompt, chat_id=chat_id)
    if not starter_text:
        starter_text = "Ooo, qani suhbatni boshladik! Kimda nima gap, nimalar bo'lyapti? 😎"

    reply_content = (
        f"🎙 **Suhbat boshlandi!** 😎\n\n"
        f"{starter_text}\n\n"
        f"*(Menga gapirish uchun ushbu xabarimga **Reply** qiling yoki @ atmetka qiling! To'xtatish uchun: /stop_suhbatdosh)*"
    )

    sent = await message.answer(reply_content, parse_mode="Markdown")

    # Javobni bazaga saqlash
    await database.add_message(
        chat_id=chat_id,
        role="assistant",
        content=starter_text,
        token_count=ai_service.estimate_tokens(starter_text)
    )


@group_router.message(Command("stop_suhbatdosh", "stop"))
@group_router.message(F.text.lower().startswith("/stop-suhbatdosh") | F.text.lower().startswith("/stop_suhbatdosh"))
async def cmd_stop_chat(message: Message) -> None:
    """Suhbatni to'xtatish buyrug'i: faol rejimni o'chiradi."""
    chat_id = message.chat.id
    await database.set_chat_state(chat_id, "active_mode", "0")

    stop_text = (
        "Suhbat to'xtatildi! 🛑\n\n"
        "Endi men umumiy gaplarga qo'shilmayman. Faqat meni atmetka qilsangiz yoki xabarlarimga **Reply** qilsangizgina javob beraman.\n\n"
        "Qayta suhbatni faollashtirish uchun: /suhbat_boshlash 😎"
    )
    await message.reply(stop_text, parse_mode="Markdown")


@group_router.message()
async def handle_group_message(message: Message) -> None:
    """
    Guruhdagi xabarlarni saralash va qoidalar bo'yicha javob qaytarish:
    1. Har qanday xabar bazaga saqlanadi (kontekst yo'qolmasligi uchun).
    2. Botga atmetka qilinganda -> javob beradi.
    3. Bot xabariga Reply qilinganda -> javob beradi.
    4. Suhbat faol bo'lsa (/suhbat_boshlash) -> 10 ta xabardan 2 tasiga ora-orada qo'shiladi.
    5. Boshqa paytda jim turadi.
    """
    # Botlarning xabarlarini e'tiborsiz qoldirish
    if message.from_user and message.from_user.is_bot:
        return

    # Matn, izoh yoki stikerlarni qabul qilish
    text = message.text or message.caption
    if not text and message.sticker:
        emoji = message.sticker.emoji or "🎨"
        text = f"[Stiker: {emoji}]"

    if not text:
        return

    sender_name = message.from_user.full_name if message.from_user else "Foydalanuvchi"
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None

    try:
        # 1. Xabarni doim bazaga yozish (kontekst uchun)
        user_tokens = ai_service.estimate_tokens(text)
        await database.add_message(
            chat_id=chat_id,
            role="user",
            content=text,
            user_id=user_id,
            sender_name=sender_name,
            token_count=user_tokens
        )

        # Bot haqida ma'lumot
        bot_info = await message.bot.get_me()
        bot_username = (bot_info.username or "").lower()
        bot_id = bot_info.id

        text_lower = text.lower()

        # Atmetka (mention) tekshiruvi:
        is_mentioned = False
        if bot_username and f"@{bot_username}" in text_lower:
            is_mentioned = True
        elif message.entities:
            for ent in message.entities:
                if ent.type == "mention":
                    m_text = text[ent.offset:ent.offset + ent.length].lower()
                    if m_text == f"@{bot_username}":
                        is_mentioned = True
                elif ent.type == "text_mention" and ent.user and ent.user.id == bot_id:
                    is_mentioned = True

        # Reply tekshiruvi (botning xabariga reply qilinganmi?):
        is_reply_to_bot = False
        if message.reply_to_message and message.reply_to_message.from_user:
            if message.reply_to_message.from_user.id == bot_id:
                is_reply_to_bot = True

        # Faol suhbat rejimi tekshiruvi:
        is_active_mode = (await database.get_chat_state(chat_id, "active_mode", "0")) == "1"

        # 10 ta xabardan 2 tasiga ora-orada qo'shilish hisoblagichi
        counter = await database.increment_chat_counter(chat_id)
        is_occasional = (counter % 10 in (3, 8))

        # Javob berish shartlari:
        should_reply = False
        if is_mentioned:
            should_reply = True
        elif is_reply_to_bot:
            should_reply = True
        elif is_active_mode and is_occasional:
            should_reply = True

        # Agar shartlar bajarilmasa, bot javob bermaydi
        if not should_reply:
            return

        # 2. Telegramda "yozmoqda..." statusini yoqish
        try:
            await message.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception as e:
            logger.debug("ChatAction TYPING xatosi: %s", e)

        # 3. AI uchun kontekstni yig'ish (oxirgi 30 ta xabar + summary)
        context_messages = await ai_service.build_context_messages(chat_id)

        # 4. AI dan javob olish
        ai_reply = await ai_service.request_ai_response(context_messages, chat_id=chat_id)

        # 5. Javobni bazaga saqlash
        assistant_tokens = ai_service.estimate_tokens(ai_reply)
        await database.add_message(
            chat_id=chat_id,
            role="assistant",
            content=ai_reply,
            token_count=assistant_tokens
        )

        # 6. Matnli xabar yuborish
        chunks = split_text(ai_reply, chunk_size=4000)
        for chunk in chunks:
            try:
                await message.reply(chunk, parse_mode="Markdown")
            except Exception:
                try:
                    await message.reply(chunk)
                except Exception as e:
                    logger.error("Guruhga javob yuborishda xatolik: %s", e)

    except Exception as exc:
        logger.error("Xabarni qayta ishlashda kutilmagan xatolik yuz berdi: %s", exc, exc_info=True)
        try:
            await message.reply("Kechirasiz, xabaringizni qayta ishlashda qisqa uzilish bo'ldi. Yana bir bor yozing! 😎")
        except Exception:
            pass
