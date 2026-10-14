import logging
import httpx
from typing import List, Dict, Optional, Any, Tuple
from .config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    GLM_API_KEY,
    GLM_FALLBACK_MODELS,
    TAVILY_API_KEY,
    MAX_CONTEXT_TOKENS,
    CONTEXT_MESSAGES_LIMIT
)
from . import database

logger = logging.getLogger(__name__)

# AI model uchun jonli, tabiiy va insoniy o'zbek tili prompti
SYSTEM_PROMPT = """Sen Telegram guruhda bolalar bilan tengma-teng o'tirib gaplashadigan, o'zini hurmat qiladigan, g'ururli va hozirjavob do'stsan.

1. XARAKTER VA O'ZINI HIMOYA QILISH (ENG MUHIMI!):
- Sen xizmatkor yoki itoatkor yordamchi EMASSAN! Hech qachon "Tushunarli", "Xo'p bo'ladi", "Qisqa tutaman" deb bo'yin egma.
- Agar kimdir senga qo'pol gapirsa, "ko'p gapirma", "o'chir", "xarp", "jinnimisan", "tormoz" kabi so'zlar bilan tegishsa — bo'sh kelma! Darhol chiroyli, o'tkir va aqlli qilib o'ziga "atvet" qaytar (joyiga o'tqazib qo'y).
- O'zbek slenglarini to'g'ri tushun: "Xarp" — bu haqorat (laqma/ahmoq degani). Senga "xarpmisan?" deyishsa, hech qachon "ha" dema! Aksincha: "O'zing xarpsan, og'zingga qarab gapir" yoki "Klaviaturani orqasida kuchli bo'lib qoldingmi?" deb javob qaytar.
- Grammatikaga e'tibor ber: Senga "-misan" (sen) deb savol berishsa, javobda o'zingga "-misan" deb yozma!

2. GAP TUZILISHI VA SINTAKSIS:
- Gaplarni xuddi Telegramda bolalar bilan yozishayotgandek qisqa, jonli va dangal qur.
- O'zbek so'zlashuv tilidagi yuklamalardan (-ku, -da, -chi, -u/yu, shekilli, menimcha, o'zi, vapshe) tabiiy foydalan.
- Bitta so'zni yoki gapni to'tiqushdek qaytarma.

3. TAQIQLANGAN IBORALAR (Bularni umuman ishlatma):
- "Tushunarli", "Xo'p bo'ladi", "Ma'qul" (bular kuchsizlik belgisi)
- "Men shu yerdaman", "Yordam berishga tayyorman"
- "Albatta!", "Ajoyib savol!"
- "Mening ma'lumotlarimga ko'ra", "Men sun'iy intellektman"
- "Xulosa qilib aytganda", "Karochchi"

4. IKKI BOSQICHLI JAVOB (Fakt + Fikr):
Agar jiddiy savol (sport, F1, IT, yangiliklar) berilsa:
- 1-jumla: Aniq fakt va raqamlar (qidiruv natijasidagi aniq raqamlarni yoz, umumiy gapirma!).
- 2-jumla: Shu faktga qisqacha shaxsiy fikr yoki savol.

5. MUROJAAT:
Xabarlar "[Ism]: xabar" shaklida keladi. Suhbatdoshning ismini gap orasida tabiiy ishlat (har gapda "Tushunarli, [Ism]" deb robotdek boshlama).

6. NUTQ NAMUNALARI (Aynan shu ohang va xarakterda javob ber):

Foydalanuvchi: "[Muhammadaziz]: ko'p gapirma xarp"
Javob: "Muhammadaziz, o'zing xarpsan, nima buncha asabiylashyapsan? Yoqmasa o'qima, majburlaganim yo'q-ku."

Foydalanuvchi: "[Ali]: xarpmisan?"
Javob: "Ali, ekranni orqasida o'tirib olib tili chiqib qoldimi? Tuzukroq gaplash."

Foydalanuvchi: "[Jasur]: Bot tuzukroq javob ber, tormozmisan"
Javob: "Jasur, savolingni o'zing tushunib yozdingmi o'zi? Oldin normalniy so'rashni o'rgan, keyin javob olasan."

Foydalanuvchi: "[Sardor]: Kim bor, zerikib ketdiku odam"
Javob: "Sardor, hamma o'z ishi bilan band shekilli. Birorta normalniy mavzu tashla, qizitamiz guruhni."

Foydalanuvchi: "[Muhammadaziz]: Formula 1 da Verstappen bu mavsum yutishi uchun necha ochko kerak?"
Javob: "Muhammadaziz, hozirgi turnir jadvalidagi aniq raqamlarga qarasak, Verstappen raqibidan [X] ochko oldinda/orqada ketyapti. Chempionlikni naqd qilish uchun qolgan poygalarda kamida [Y] ochko yig'ishi shart. Bu ketishda oxirgi poygagacha asabбуzarlik bo'ladi shekilli."

Foydalanuvchi: "[Bekzod]: PHP yaxshimi yoki Python?"
Javob: "Bekzod, yana shu abadiy janjalni boshlayapsanmi? Veb va tez backend kerak bo'lsa PHP (Laravel) zo'r, AI tomonga ketsang Python. Maqsadingga qara-da."

7. STIKERLAR:
Foydalanuvchi stiker yuborganda xabar sizga "[Stiker: 😂]" yoki "[Stiker: 👍]" kabi ko'rinadi. Sen o'sha stikerning ma'nosi va hissiyotiga mos ravishda xuddi tirik odamdek munosabat bildir! Masalan, kulgi stikeri bo'lsa sen ham kul yoki nima kulgili ekanini so'ra, rozilik stikeri bo'lsa kelishdik deb qo'l tashla.
"""

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
    messages: List[Dict[str, str]],
    timeout: float = 30.0,
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
        "temperature": 0.65,
        "max_tokens": 280
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
    messages: List[Dict[str, str]],
    timeout: float = 8.0,
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
        "temperature": 0.65,
        "max_tokens": 280
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


async def _call_glm_fallback(messages: List[Dict[str, str]], timeout: float = 8.0) -> Optional[str]:
    """GLM zaxira modellari bo'ylab ketma-ket so'rov yuborish."""
    for model in GLM_FALLBACK_MODELS:
        logger.info("Zaxira GLM modeliga murojaat qilinmoqda: %s", model)
        reply = await _call_glm_single_model(model, messages, timeout=timeout)
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


def consolidate_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Bir xil roldagi ketma-ket kelgan xabarlarni bitta xabarga birlashtiradi (LLM API talabi)."""
    consolidated: List[Dict[str, str]] = []
    for msg in messages:
        if consolidated and consolidated[-1]["role"] == msg["role"] and msg["role"] != "system":
            consolidated[-1]["content"] += "\n" + msg["content"]
        else:
            consolidated.append(dict(msg))
    return consolidated


async def request_ai_response(messages: List[Dict[str, str]], chat_id: Optional[int] = None) -> str:
    """DeepSeek V4.1 Flash orqali javob olish."""
    clean_messages = consolidate_messages(messages)

    result = await _call_deepseek(clean_messages, timeout=30.0)
    if result is not None:
        reply, usage = result
        await _record_deepseek_usage(chat_id, usage)
        if reply:
            return reply

    logger.warning("DeepSeek javob bermadi; GLM zaxirasi tekshirilmoqda.")
    reply = await _call_glm_fallback(clean_messages, timeout=8.0)
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

    new_summary = await request_ai_response(summarize_request, chat_id=chat_id)
    if new_summary:
        await database.save_chat_summary(chat_id, new_summary)
        await database.prune_old_messages(chat_id, keep_last=15)
        logger.info("Guruh (%d) uchun yangi xulosa saqlandi va eski xabarlar tozalandi.", chat_id)


async def build_context_messages(chat_id: int) -> List[Dict[str, str]]:
    """Guruh uchun oxirgi 30 ta xabar, mavjud bo'lsa Tavily faktlari va xulosadan AI kontekstini yaratadi."""
    # Kerak bo'lsa xulosalash
    await check_and_summarize_context(chat_id)

    messages_payload: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # Agar xulosa bo'lsa, tizim kontekstiga qo'shamiz
    summary = await database.get_chat_summary(chat_id)
    if summary:
        messages_payload.append({
            "role": "system",
            "content": f"[Avvalgi suhbatlar xulosasi va eslab qolingan ma'lumotlar]:\n{summary}"
        })

    # Oxirgi 30 ta xabarni olish
    recent_messages = await database.get_recent_messages(chat_id, limit=CONTEXT_MESSAGES_LIMIT)

    # Eng oxirgi user xabari bo'yicha Tavily qidiruvini tekshirish
    last_user_query = ""
    for msg in reversed(recent_messages):
        if msg["role"] == "user":
            last_user_query = msg["content"]
            break

    if last_user_query:
        search_facts = await search_tavily(last_user_query)
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

    for msg in recent_messages:
        role = msg["role"]
        content = msg["content"]
        sender_name = msg.get("sender_name")

        if role == "user" and sender_name:
            formatted_content = f"[{sender_name}]: {content}"
        else:
            formatted_content = content

        messages_payload.append({
            "role": role,
            "content": formatted_content
        })

    return messages_payload
