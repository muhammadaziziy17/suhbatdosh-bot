"""
Legenda Suhbatdosh botining barcha modullarini tekshiruvchi test skripti.
"""
import asyncio
import os
import sys

# src modulini topishi uchun yo'l qo'shamiz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


async def test_all():
    print("=== 1. Konfiguratsiyani tekshirish ===")
    from src import config
    print(f"Bot token mavjud: {bool(config.TELEGRAM_BOT_TOKEN)}")
    print(f"DeepSeek API mavjud: {bool(config.DEEPSEEK_API_KEY)} (Model: {config.DEEPSEEK_MODEL})")
    print(f"GLM zaxirasi mavjud: {bool(config.GLM_API_KEY)} (Modellar: {config.GLM_FALLBACK_MODELS})")
    print(f"Memes papkasi yo'li: {config.MEMES_DIR} (Mavjud: {config.MEMES_DIR.exists()})")

    print("\n=== 2. Ma'lumotlar bazasini tekshirish ===")
    from src import database
    await database.init_db()
    test_chat_id = -999999

    # Tozalash
    await database.clear_chat_history(test_chat_id)

    # Xabar qo'shish
    msg_id = await database.add_message(
        chat_id=test_chat_id,
        role="user",
        content="Salom bot!",
        user_id=12345,
        sender_name="Ali",
        token_count=10
    )
    print(f"Test xabar qo'shildi, ID: {msg_id}")

    # Xabarlarni olish
    recent = await database.get_recent_messages(test_chat_id, limit=30)
    print(f"Olingan xabarlar soni: {len(recent)}, Birinchi xabar: {recent[0]['content']}")
    assert len(recent) == 1
    assert recent[0]["content"] == "Salom bot!"

    # Tokenlar soni
    total_tokens = await database.get_total_chat_tokens(test_chat_id)
    print(f"Umumiy tokenlar soni: {total_tokens}")
    assert total_tokens == 10

    # Xulosa saqlash va olish
    await database.save_chat_summary(test_chat_id, "Test xulosa")
    summary = await database.get_chat_summary(test_chat_id)
    print(f"Xulosa: {summary}")
    assert summary == "Test xulosa"

    # Holat (state) tekshirish
    await database.set_state("test_key", "test_val")
    val = await database.get_state("test_key")
    print(f"State test: {val}")
    assert val == "test_val"

    # Tozalash
    await database.clear_chat_history(test_chat_id)
    print("Ma'lumotlar bazasi testi muvaffaqiyatli yakunlandi!")

    print("\n=== 3. Profil rasmlari va avtomatik jadvalni tekshirish ===")
    from src.avatar_service import get_meme_images, setup_avatar_scheduler
    images = get_meme_images()
    print(f"Topilgan rasmlar soni: {len(images)}")
    if images:
        print(f"Birinchi 3 ta rasm: {[img.name for img in images[:3]]}")
        assert len(images) > 0

    avatar_scheduler = setup_avatar_scheduler(object())
    assert avatar_scheduler.get_job("daily_avatar_rotation") is not None
    avatar_scheduler.shutdown(wait=False)
    print("Profil rasmi har kuni UTC 00:00 da almashtirish jadvali tayyor.")

    print("\n=== 4. AI Xizmatini tekshirish (DeepSeek V4.1 Flash / ixtiyoriy GLM) ===")
    from src import ai_service
    test_messages = [
        {"role": "system", "content": ai_service.SYSTEM_PROMPT},
        {"role": "user", "content": "[Aziz]: Salom Legenda! Qandaysan?"}
    ]
    response = await ai_service.request_ai_response(test_messages)
    print(f"AI Javobi (boshlang'ich 150 belgisi):\n{response[:150]}...")
    assert len(response) > 5

    print("\n=== BARCHA TESTLAR A'LO DARAJADA O'TDI! ===")

if __name__ == "__main__":
    asyncio.run(test_all())
