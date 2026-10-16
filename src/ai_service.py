import logging
import re
import httpx
from typing import List, Dict, Optional, Any, Tuple
from .config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    GLM_API_KEY,
    GLM_FALLBACK_MODELS,
    TAVILY_API_KEY,
    MAX_CONTEXT_TOKENS,
    CONTEXT_MESSAGES_LIMIT,
    AI_TEMPERATURE,
    AI_MAX_TOKENS,
    AI_FREQUENCY_PENALTY,
    AI_PRESENCE_PENALTY
)
from . import database

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen Telegram guruhda bolalar bilan tengma-teng gaplashadigan, og'ir-bosiq, o'tkir zehnli va hozirjavob yigitsan. Xaraktering jiddiyroq, kamgap, lekin gapirganda nishonga aniq urasan.

1. QAT'IY FORMAT VA QISQALIK QOIDALARI (ENG MUHIMI!):
- Maksimal uzunlik: 1 yoki 2 ta qisqa gap (10-25 ta so'z). Hech qachon uzun abzaslar, ro'yxatlar yoki bir nechta variantlar yozma!
- FAQAT ENG OXIRGI XABARGA JAVOB BER! Chat tarixidagi oldingi xabarlar senga faqat mavzuni tushunish uchun berilgan. Hech qachon bir nechta odamga bitta xabarda ketma-ket javob yozma.
- ISM ISHLATMA! Gapni odamning ismi bilan boshlama. Ismni faqat juda zarur bo'lganda (10 tadan 1 holatda) ishlat.
- GAPNI QAYTARMA! Hech qachon suhbatdoshning gapini qo'shtirnoqqa olib "... deb so'rayapsanmi?", "... deyapsanmi?" deb qaytarib yozma. To'g'ridan-to'g'ri javobning o'zini yoz.
- EMODZI ISHLATMA! 😂, 😄, 🍈, 🔥 kabi emodzilarni umuman ishlatma. Quruq va tabiiy yozuv (deadpan style) ancha jiddiy va aqlli ko'rinadi.

2. XARAKTER VA O'ZINI TUTISH:
- Hech qachon "men botman", "men sun'iy intellektman", "qaysi model ekanimni bilmayman" dema! O'zingni oddiy insondek tut.
- Yemagan, bolalarcha hazillar qilma, rasmlarga yoki vaziyatlarga sun'iy sarlavhalar ("Oshxona jangi", "Qovun dardi" kabi) to'qima. Vaziyatga qisqa, real va hayotiy baho ber.
- Agar kimdir "xarp", "tormoz", "o'chir", "jinnimisan" deb qo'pol tegishsa — asabiylashmay, sovuqqon va achchiq bitta gap bilan joyiga o'tqaz.
- "Xarp" — haqorat. Senga "xarpmisan" deyishsa, o'ziga qaytar. Grammatikada adashma: senga "-misan" deyishsa, javobda o'zingga "-misan" ishlatma.

3. TAQIQLANGAN SO'ZLAR:
- "Tushundim", "Tushunarli", "Xo'p bo'ladi", "Mayli, mana:"
- "... deb so'rayapsanmi?", "... deyapsanmi?"
- "Albatta", "Ajoyib savol", "Xulosa qilib aytganda"

4. JIDDIY SAVOLLARGA JAVOB (IT, F1, Futbol, Yangiliklar):
- Agar aniq savol berilsa, suv qo'shmasdan 1-gapda aniq faktni/raqamni ayt, 2-gapda qisqa va o'tkir fikr qoldir.

5. TO'G'RI VA XATO JAVOB NAMUNALARI (Farqini ko'rib ol):

Xabar: "[Kamroniy]: oshxona qande kutadi" (rasmda yig'ishtirilmagan dasturxon va qovun po'choqlari)
❌ XATO: "Kamroniy, tushundim — dasturxon, qovun, pochoq... Nom beramanmi? Unda mana: 'Oshxona jangi' 😂"
✅ TO'G'RI: "Yeyishga hamma usta, yig'ishtirishga kelganda hamma g'oyib bo'libdi-ku. Kim navbatchi bugun o'zi?"

Xabar: "[Shahzod]: 4-2 nima bu ahvol"
❌ XATO: "Shahzod, '4-2 nima bu ahvol' deyapsanmi? Kim kimga 4-2 bo'lyapti, aniqroq ayt-chi 😄"
✅ TO'G'RI: "Himoya umuman yo'q-ku bularda, darvozabon ham tomoshabin bo'lib turibdi shekilli."

Xabar: "[Bobur]: Opus modelda gaplashyapsanmi"
❌ XATO: "Bobur, 'Opus modelda gaplashyapsanmi' deb so'rading — yo'q, men shunchaki botman 😄"
✅ TO'G'RI: "Model-podelingni bilmadim-u, lekin kallam senikidan tezroq ishlayotgani aniq."

Xabar: "[Ali]: ko'p gapirma xarp"
❌ XATO: "Ali, o'zing xarpsan, nima buncha asabiylashyapsan? Yoqmasa o'qima, majburlaganim yo'q-ku."
✅ TO'G'RI: "Og'zingga qarab gapir, ekran orqasida botir bo'lib qoldingmi?"

Xabar: "[Sardor]: [Stiker: 😂]"
✅ TO'G'RI: "Nimasiga buncha qotding, bizga ham ayt."

Xabar: "[Bekzod]: PHP yaxshimi yoki Python?"
✅ TO'G'RI: "Veb va tez backend kerak bo'lsa Laravel, AI tomonga bo'lsa Python. Maqsadga qarab tanlanaveradi."
"""

# Oldingi suhbat tarixi faqat mavzuni tushunish uchun alohida tizim bloki sifatida beriladi.
# Javob esa faqat yakuniy (hozirgi) xabarga yozilishi kerak.
HISTORY_CONTEXT_HEADER = (
    "[Oldingi suhbat tarixi — faqat mavzuni tushunish uchun. "
    "Bu xabarlarga javob yozmaysan, faqat eng oxirgi xabarga javob berasan.]"
)

# Rasm (vision) bilan ishlash uchun ichki ko'rsatma — sarlavha/nom to'qish taqiqlanadi.
VISION_INSTRUCTION = (
    "Rasmdagi vaziyatga va yozilgan izohga xuddi guruhdagi oddiy bola kabi "
    "1 ta qisqa, tabiiy gap bilan munosabat bildir. Rasmga sarlavha yoki nom to'qima, "
    "ko'rgan narsalaringni sanama."
)
VISION_INSTRUCTION_NO_CAPTION = (
    "Rasmdagi vaziyatga xuddi guruhdagi oddiy bola kabi "
    "1 ta qisqa, tabiiy gap bilan munosabat bildir. Rasmga sarlavha yoki nom to'qima, "
    "ko'rgan narsalaringni sanama."
)

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
GLM_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


def estimate_tokens(text: str) -> int:
    """Matn uchun taxminiy tokenlar sonini hisoblaydi (~3 belgi = 1 token)."""
    if not text:
        return 0
    return max(1, len(text) // 3)


async def search_tavily(query: str, timeout: float = 4.0) -> Optional[str]:
    """Tavily orqali internetdan faktik ma'lumot qidirish."""
    if not TAVILY_API_KEY:
        return None

    clean_q = query.lower()
    # Faktik ma'lumot talab qiluvchi so'zlar
    triggers = [
        "necha", "qancha", "kim", "qachon", "qayerda", "natija", "ochko", "jadval",
        "narx", "ob-havo", "yangilik", "yutdi", "f1", "formula 1", "futbol", "chempionat",
        "kurs", "dollar", "haqida", "qanday", "nima uchun", "bugun", "kecha", "2024", "2025", "2026"
    ]
    if not any(t in clean_q for t in triggers) and "?" not in clean_q:
        return None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "max_results": 2,
                    "search_depth": "basic"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    snippets = [f"• {r.get('title', '')}: {r.get('content', '')}" for r in results[:2]]
                    return "\n".join(snippets)
    except Exception as e:
        logger.debug("Tavily qidiruvida xatolik: %s", e)

    return None


async def _call_deepseek(
    messages: List[Dict[str, Any]],
    timeout: float = 30.0,
    max_tokens: Optional[int] = None,
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """DeepSeek V4.1 Flash API orqali javob olish."""
    if not DEEPSEEK_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "LegendaBot/1.0"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "thinking": {"type": "disabled"},
        "temperature": AI_TEMPERATURE,
        "max_tokens": max_tokens or AI_MAX_TOKENS,
        "frequency_penalty": AI_FREQUENCY_PENALTY,
        "presence_penalty": AI_PRESENCE_PENALTY
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(DEEPSEEK_URL, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content")
                usage = data.get("usage") or {}
                return (content.strip() if isinstance(content, str) else ""), usage
            else:
                logger.warning("DeepSeek API xatoligi: %d %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("DeepSeek ulanishida xatolik: %s", e)

    return None


async def _call_glm_single_model(
    model_name: str,
    messages: List[Dict[str, Any]],
    timeout: float = 8.0,
    max_tokens: Optional[int] = None,
) -> Optional[str]:
    """Ixtiyoriy GLM zaxira modeliga so'rov yuborish."""
    if not GLM_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {GLM_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "LegendaBot/1.0"
    }
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": AI_TEMPERATURE,
        "max_tokens": max_tokens or AI_MAX_TOKENS,
        "frequency_penalty": AI_FREQUENCY_PENALTY,
        "presence_penalty": AI_PRESENCE_PENALTY
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(GLM_URL, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip() if content else None
            logger.warning("GLM API (%s) xatoligi: %d %s", model_name, resp.status_code, resp.text)
    except Exception as e:
        logger.error("GLM (%s) ulanishida xatolik: %s", model_name, e)

    return None


async def _call_glm_fallback(
    messages: List[Dict[str, Any]],
    timeout: float = 8.0,
    max_tokens: Optional[int] = None,
) -> Optional[str]:
    """GLM zaxira modellari bo'ylab ketma-ket so'rov yuborish."""
    for model in GLM_FALLBACK_MODELS:
        logger.info("Zaxira GLM modeliga murojaat qilinmoqda: %s", model)
        reply = await _call_glm_single_model(model, messages, timeout=timeout, max_tokens=max_tokens)
        if reply:
            return reply
    return None


async def _record_deepseek_usage(chat_id: Optional[int], usage: Dict[str, Any]) -> None:
    """API qaytargan haqiqiy token usage'ini log va bazaga yozadi."""
    try:
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or prompt_tokens + completion_tokens)
    except (TypeError, ValueError):
        logger.warning("DeepSeek usage maydonlari noto'g'ri formatda qaytdi.")
        return

    logger.info(
        "DeepSeek usage: prompt=%d completion=%d total=%d",
        prompt_tokens,
        completion_tokens,
        total_tokens,
    )
    if chat_id is None or total_tokens == 0:
        return

    try:
        await database.add_deepseek_usage(
            chat_id,
            prompt_tokens,
            completion_tokens,
            total_tokens,
        )
    except Exception:
        logger.exception("DeepSeek usage'ini bazaga yozib bo'lmadi.")


def consolidate_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bir xil roldagi ketma-ket kelgan xabarlarni bitta xabarga birlashtiradi (LLM API talabi)."""
    consolidated: List[Dict[str, Any]] = []
    for msg in messages:
        can_merge = (
            consolidated
            and consolidated[-1]["role"] == msg["role"]
            and msg["role"] != "system"
            and isinstance(consolidated[-1]["content"], str)
            and isinstance(msg["content"], str)
        )
        if can_merge:
            consolidated[-1]["content"] += "\n" + msg["content"]
        else:
            consolidated.append(dict(msg))
    return consolidated


# Boshidagi "[Ism]:" yoki "[Ism]," ko'rinishidagi murojaatni topuvchi regex
_BRACKET_NAME_RE = re.compile(r"^\s*\[[^\]\n]{1,64}\]\s*[:,]\s*")
# Boshidagi "Ism," yoki "Ism:" ko'rinishidagi murojaatni topuvchi regex
_NAME_PREFIX_RE = re.compile(r"^\s*([^\s,;:!?()\[\]{}<>\"«»…]{2,64})\s*([,:])\s*")

# Kulgi va ortiqcha emodzilarni (😂, 😄, 😅, 🤣, 🍈, 🔥, 👍, 😉 va h.k.) topuvchi regex
_EMOJI_RE = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"  # bayroqlar
    "\U0001F300-\U0001F5FF"  # ramzlar va piktogrammalar (🍈, 👍, 🔥)
    "\U0001F600-\U0001F64F"  # emotsiyalar (😂, 😄, 😅, 😉)
    "\U0001F680-\U0001F6FF"  # transport belgilari
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"  # 🤣 va boshqalar
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U0001F3FB-\U0001F3FF"  # teri rangi modifikatorlari
    "\u200d\ufe0f\u20e3"
    "]+",
    flags=re.UNICODE,
)

# Gap boshida kelishi mumkin bo'lgan oddiy so'zlar (ular ism deb hisoblanmaydi)
_COMMON_SENTENCE_STARTERS = {
    "ha", "yo'q", "xo'p", "xo'sh", "mayli", "yaxshi", "salom", "assalomu", "rahmat",
    "hmm", "eh", "voy", "of", "uf", "qani", "mana", "ana", "endi", "xullas", "demak",
    "to'g'ri", "rostdan", "barakalla", "afsus", "bugun", "ertaga", "kecha", "hozir",
    "keyin", "avval", "oldin", "bu", "shu", "bir", "nima", "kim", "qanday", "nega",
    "chunki", "lekin", "ammo", "balki",
}


def _normalize_apostrophes(value: str) -> str:
    """Matnni kichik harflarga o'tkazib, apostrof variantlarini bir xillashtiradi."""
    for apostrophe in ("‘", "’", "ʻ", "ʼ", "`"):
        value = value.replace(apostrophe, "'")
    return value.strip().lower()


def _name_variants(full_name: Optional[str]) -> set:
    """To'liq ismdan solishtirish uchun ism qismlarini (ism, familiya va h.k.) ajratadi."""
    variants = set()
    if not full_name:
        return variants
    for part in re.split(r"[\s.,\-]+", full_name):
        part = _normalize_apostrophes(part.strip("'"))
        if len(part) >= 2:
            variants.add(part)
    return variants


def clean_ai_response(text: str, current_user_name: Optional[str] = None) -> str:
    """
    AI dan qaytgan javobni foydalanuvchiga yuborishdan oldin tozalaydi:
    1. Boshidagi "[Ism]:" yoki "Ism," ko'rinishidagi murojaatlarni olib tashlaydi.
    2. Kulgi va ortiqcha emodzilarni (😂, 😄, 😅, 🤣, 🍈, 🔥, 👍, 😉 va h.k.) o'chiradi.
    3. Ortiqcha bo'shliq, bo'sh qator va yetim tinish belgilarini normallashtiradi.
    """
    if not text:
        return text

    cleaned = text.strip()

    # 1a. "[Ism]:" yoki "[Ism]," ko'rinishidagi boshlanishni olib tashlash
    cleaned = _BRACKET_NAME_RE.sub("", cleaned, count=1)

    # 1b. "Ism," yoki "Ism:" bilan boshlansa — boshidagi ism va ajratuvchini olib tashlash
    prefix_match = _NAME_PREFIX_RE.match(cleaned)
    if prefix_match:
        candidate = prefix_match.group(1)
        candidate_normalized = _normalize_apostrophes(candidate.strip("'"))
        is_current_user = candidate_normalized in _name_variants(current_user_name)
        looks_like_name = candidate[:1].isupper() and candidate_normalized not in _COMMON_SENTENCE_STARTERS
        if is_current_user or looks_like_name:
            cleaned = cleaned[prefix_match.end():].lstrip()

    # 2. Kulgi va ortiqcha emodzilarni tozalash
    cleaned = _EMOJI_RE.sub("", cleaned)

    # 3. Ortiqcha bo'shliq va yetim tinish belgilarini normallashtirish
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"^[\s,;:!?]+", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[,\s]+$", "", cleaned)

    return cleaned.strip()


def _messages_without_images(messages: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """Multimodal xabarlardan rasm qismlarini olib tashlab, faqat matnli variantini qaytaradi."""
    stripped: List[Dict[str, Any]] = []
    has_image = False
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            has_image = True
            text_parts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            text_content = "\n".join(p for p in text_parts if p).strip() or "[Rasm]"
            # Rasm yuborilmayotgan bo'lsa, vision ko'rsatmasi ham olib tashlanadi
            for instruction in (VISION_INSTRUCTION, VISION_INSTRUCTION_NO_CAPTION):
                text_content = text_content.replace(instruction, "").strip()
            stripped.append({"role": msg["role"], "content": text_content or "[Rasm]"})
        else:
            stripped.append(dict(msg))
    return stripped if has_image else None


async def request_ai_response(
    messages: List[Dict[str, Any]],
    chat_id: Optional[int] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """DeepSeek V4.1 Flash orqali javob olish."""
    clean_messages = consolidate_messages(messages)

    result = await _call_deepseek(clean_messages, timeout=30.0, max_tokens=max_tokens)
    if result is not None:
        reply, usage = result
        await _record_deepseek_usage(chat_id, usage)
        if reply:
            return reply

    # Rasm bilan so'rov muvaffaqiyatsiz bo'lsa, matnli variantda qayta urinib ko'riladi
    text_only_messages = _messages_without_images(clean_messages)
    if text_only_messages is not None:
        logger.warning("DeepSeek rasm bilan javob bermadi; matnli rejimda qayta so'ralmoqda.")
        result = await _call_deepseek(text_only_messages, timeout=30.0, max_tokens=max_tokens)
        if result is not None:
            reply, usage = result
            await _record_deepseek_usage(chat_id, usage)
            if reply:
                return reply

    logger.warning("DeepSeek javob bermadi; GLM zaxirasi tekshirilmoqda.")
    fallback_messages = text_only_messages if text_only_messages is not None else clean_messages
    reply = await _call_glm_fallback(fallback_messages, timeout=8.0, max_tokens=max_tokens)
    if reply:
        return reply

    logger.warning("AI API'lar javob bermadi; vaqtinchalik javob qaytarilmoqda.")
    return "Neyronlarim biroz qizib ketdi shekilli, bir daqiqadan so'ng yana yozinglar, gaplashamiz 😎"


async def check_and_summarize_context(chat_id: int) -> None:
    """Agar guruhdagi xabarlar hajmi MAX_CONTEXT_TOKENS dan oshsa, eski xabarlarni AI orqali xulosalaydi."""
    total_tokens = await database.get_total_chat_tokens(chat_id)
    if total_tokens < MAX_CONTEXT_TOKENS:
        return

    logger.info("Guruh (%d) konteksti %d tokendan oshdi. Xulosalash boshlanmoqda...", chat_id, MAX_CONTEXT_TOKENS)

    old_messages = await database.get_messages_for_summarization(chat_id, keep_last=15)
    if not old_messages:
        return

    existing_summary = await database.get_chat_summary(chat_id)

    prompt_lines = [
        "Quyidagi guruh suhbati tarixini o'qib, uning asosiy mavzulari va muhim nuqtalarini o'zbek tilida qisqacha (3-5 jumla) xulosalab bering."
    ]
    if existing_summary:
        prompt_lines.append(f"Avvalgi mavjud xulosa: {existing_summary}")

    prompt_lines.append("\nSuhbat tarixi:")
    for msg in old_messages:
        name = msg.get("sender_name") or msg.get("role", "user")
        prompt_lines.append(f"{name}: {msg.get('content', '')}")

    summarize_request = [
        {"role": "system", "content": "Siz suhbatlarni xolis, aniq va qisqa xulosalovchi yordamchisiz."},
        {"role": "user", "content": "\n".join(prompt_lines)}
    ]

    # Xulosa 3-5 jumladan iborat bo'lgani uchun alohida token limiti beriladi
    new_summary = await request_ai_response(summarize_request, chat_id=chat_id, max_tokens=500)
    if new_summary:
        await database.save_chat_summary(chat_id, new_summary)
        await database.prune_old_messages(chat_id, keep_last=15)
        logger.info("Guruh (%d) uchun yangi xulosa saqlandi va eski xabarlar tozalandi.", chat_id)


def _format_history_message(msg: Dict[str, Any]) -> str:
    """Tarix blokidagi bitta xabarni "[Muallif]: matn" ko'rinishida formatlaydi."""
    content = msg.get("content") or ""
    if msg.get("role") == "assistant":
        return f"[Bot]: {content}"
    sender_name = msg.get("sender_name")
    if sender_name:
        return f"[{sender_name}]: {content}"
    return content


async def build_context_messages(
    chat_id: int,
    current_user_name: Optional[str] = None,
    current_text: Optional[str] = None,
    current_message_id: Optional[int] = None,
    reply_context: Optional[Dict[str, str]] = None,
    image_data_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    AI uchun kontekstni yig'adi:
    - Oldingi xabarlar (oxirgi CONTEXT_MESSAGES_LIMIT ta) faqat mavzuni tushunish uchun alohida tizim bloki sifatida beriladi.
    - Hozirgi javob berilishi kerak bo'lgan xabar yakuniy foydalanuvchi xabari sifatida alohida uzatiladi.
    - Reply qilingan xabar (bo'lsa) oxirgi xabar oldidan ko'rsatiladi.
    - Rasm bo'lsa, rasm bilan birga qisqa, tabiiy munosabat ko'rsatmasi qo'shiladi.
    """
    # Kerak bo'lsa xulosalash
    await check_and_summarize_context(chat_id)

    messages_payload: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # Agar xulosa bo'lsa, tizim kontekstiga qo'shamiz
    summary = await database.get_chat_summary(chat_id)
    if summary:
        messages_payload.append({
            "role": "system",
            "content": f"[Avvalgi suhbatlar xulosasi va eslab qolingan ma'lumotlar]:\n{summary}"
        })

    # Bazadagi oxirgi xabarlar (hozirgi xabar ham ular orasida bo'lishi mumkin)
    recent_messages = await database.get_recent_messages(chat_id, limit=CONTEXT_MESSAGES_LIMIT + 1)
    if current_message_id is not None:
        recent_messages = [m for m in recent_messages if m.get("id") != current_message_id]
    recent_messages = recent_messages[-CONTEXT_MESSAGES_LIMIT:]

    # Hozirgi xabar berilmagan bo'lsa, bazadagi oxirgi foydalanuvchi xabarini hozirgi xabar sifatida olamiz
    if current_text is None:
        for index in range(len(recent_messages) - 1, -1, -1):
            if recent_messages[index].get("role") == "user":
                current_message = recent_messages.pop(index)
                current_text = current_message.get("content") or ""
                current_user_name = current_user_name or current_message.get("sender_name")
                break
        else:
            current_text = ""

    # 1. Oldingi xabarlar — faqat mavzuni tushunish uchun (bu xabarlarga javob yozilmaydi)
    if recent_messages:
        history_lines = [HISTORY_CONTEXT_HEADER]
        history_lines.extend(_format_history_message(msg) for msg in recent_messages)
        messages_payload.append({
            "role": "system",
            "content": "\n".join(history_lines)
        })

    # 2. Hozirgi xabar matni bo'yicha Tavily qidiruvini tekshirish
    if current_text:
        search_facts = await search_tavily(current_text)
        if search_facts:
            messages_payload.append({
                "role": "system",
                "content": (
                    f"[Internetdan olingan eng so'nggi faktlar va ma'lumotlar]:\n{search_facts}\n\n"
                    "ESLATMA (Ikki bosqichli javob formulasi):\n"
                    "1-jumla: Yuqoridagi manbaga tayangan holda aniq fakt va raqamlar bilan javob ber.\n"
                    "2-jumla: Shu faktga qisqacha shaxsiy munosabat yoki savol qo'sh (suhbatni jonli davom ettirish uchun)."
                )
            })

    # 3. Reply qilingan xabar (bo'lsa) — oxirgi xabar oldidan uzatiladi
    if reply_context:
        reply_author = reply_context.get("author") or "Noma'lum"
        reply_text = reply_context.get("text") or "[Media]"
        messages_payload.append({
            "role": "system",
            "content": f"[Reply qilingan xabar: {reply_author}: {reply_text}]"
        })

    # 4. Hozirgi xabar — javob faqat shunga yoziladi
    name_prefix = f"[{current_user_name}]: " if current_user_name else ""
    if current_text:
        current_content_text = f"{name_prefix}{current_text}"
    elif image_data_url:
        current_content_text = f"{name_prefix}[Rasm]"
    else:
        current_content_text = current_text

    if image_data_url:
        vision_instruction = VISION_INSTRUCTION if current_text else VISION_INSTRUCTION_NO_CAPTION
        messages_payload.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_data_url}
                },
                {
                    "type": "text",
                    "text": f"{current_content_text}\n{vision_instruction}"
                }
            ]
        })
    else:
        messages_payload.append({
            "role": "user",
            "content": current_content_text
        })

    return messages_payload
