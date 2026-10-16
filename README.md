# 🤖 Suhbatdosh — Telegram AI Guruhi Boti

**Suhbatdosh** — o'zbek tilida tabiiy va erkin muloqot qiluvchi aqlli Telegram bot. U guruh va superguruhlarda suhbatlashish uchun maxsus ishlab chiqilgan: bot suhbat kontekstini eslab qoladi hamda matn, stiker va rasmlarga mos, qisqa va tabiiy tarzda munosabat bildiradi.

---

## 🚀 Asosiy Imkoniyatlar

1. **O'zbek tilidagi AI suhbat (DeepSeek V4.1 Flash)**:
   - DeepSeek API orqali `deepseek-flash` modelidan foydalanadi.
   - DeepSeek API javob bermasa, `GLM_API_KEY` sozlangan bo'lsa GLM zaxirasiga o'tadi; aks holda bot qayta yozib ko'rishni so'raydi.
2. **Aqlli Guruh Xotirasi (Memory & Context)**:
   - Har bir guruhda kontekst uchun oxirgi 8 ta xabar olinadi; javob faqat eng oxirgi xabarga yoziladi.
   - Guruhdagi har bir a'zoning ismini inobatga oladi (`[Ali]: Salom`, `[Vali]: Qalaysiz`).
   - Agar kontekst juda katta bo'lib ketsa (100 000 tokendan oshsa), eski xabarlarni AI orqali qisqacha xulosalaydi (`chat_summaries`) va kontekstni doim toza va tezkor saqlaydi.
3. **Avtomatik Profil Rasmi**:
   - Bot ishga tushganda bugun hali almashtirilmagan bo'lsa yangilaydi, keyin har kuni 00:00 UTC da navbatdagi rasmni qo'yadi.
   - Railway'da ham shu bot worker jarayonining ichida ishlaydi; alohida scheduler service kerak emas.
   - Admin `/update_avatar` bilan istalgan payt qo'lda ham almashtirishi mumkin.
4. **Stikerlarni Tushunish va O'qish**:
   - Bot foydalanuvchilar yuborgan stikerlarning hissiyoti va ma'nosini (kulgi, o't, g'azab, qarsak va h.k.) tushunadi va shunga mos jonli munosabat bildiradi.
5. **Haqiqiy Ovozli Xabarlar (Golos) Yuborish**:
   - Bot faqat matn bilan cheklanib qolmaydi — `edge-tts` orqali tabiiy o'zbekcha erkak ovozida (Sardor) Telegram ovozli xabarlarini (golos) yuboradi!
   - Foydalanuvchi "ovoz tashla", "gapirchi", "eshitaylik" deb yozsa yoki suhbat davomida vaqti-vaqti bilan avtomatik ovozli xabar qilib javob beradi.
6. **Faqat Guruhlarga Moslashtirilgan Aqlli Muloqot**:
   - Guruhdagi hamma gaplarga ketavermaydi, faqat kerakli paytda gapiradi.
   - **`/suhbat_boshlash`**: Bot faol suhbatni boshlaydi ("gap boshlaydi").
   - **`/stop_suhbatdosh`**: Suhbatni to'xtatadi.
   - **Atmetka yoki Reply**: Botga @ atmetka qilinganda yoki uning xabariga **Reply** qilinganda har doim javob beradi.
   - **Ora-orada qo'shilish**: Faol suhbat vaqtida bot umumiy mavzularga ham ora-orada (har 10 ta xabardan 2 tasiga) qo'shilib turadi.
   - **Guruh cheklovi**: `.env` dagi `ALLOWED_GROUP_ID` sozlansa, bot faqat o'sha guruhda javob beradi (guruh ID sini `/chatid` orqali oling).
   - **Yaratuvchi**: "sani kim yaratgan?" deb so'ralsa, bot g'urur bilan `CREATOR_NAME` (`CREATOR_USERNAME`) ni ko'rsatadi.
   - Shaxsiy chatda esa bot faqat guruhlarda ishlashini tushuntirib, guruhga qo'shish tugmasini taqdim etadi.
5. **Server uchun 24/7 Tayyor (Systemd Service)**:
   - Linux VPS/VDS serverlarida fon rejimida uzluksiz ishlash uchun systemd fayli mavjud.

---

## 📁 Loyiha Tuzilishi

```
suhbatdosh-bot/
├── .env                          # API kalitlari va maxfiy ma'lumotlar
├── .env.example                  # Namuna konfiguratsiya fayli
├── requirements.txt              # Kerakli Python kutubxonalari
├── run.py                        # Botni ishga tushiruvchi qulay fayl
├── legenda_bot.service           # Linux server uchun systemd service fayli
├── README.md                     # Ushbu qo'llanma
├── Memes/                        # Profil rasmlari (1.jpg, 2.jpg yoki rasmlar)
├── data/                         # SQLite ma'lumotlar bazasi saqlanadigan joy
│   └── bot_database.sqlite3
├── tests/
│   └── test_all.py               # Loyihani sinovdan o'tkazish skripti
└── src/
    ├── __init__.py
    ├── config.py                 # Sozlamalar va .env yuklovchi
    ├── database.py               # Asinxron SQLite (aiosqlite)
    ├── ai_service.py             # DeepSeek, ixtiyoriy GLM zaxirasi va xulosalovchi
    ├── avatar_service.py         # Profil rasmini qo'lda almashtirish
    ├── main.py                   # Botni yurgizuvchi asosiy modul
    └── handlers/
        ├── __init__.py
        ├── group_chat.py         # Guruh xabarlarini qayta ishlash
        ├── private_chat.py       # Shaxsiy chat filtr va yo'naltirish
        └── admin.py              # Admin buyruqlari (/update_avatar, /stats)
```

---

## ⚙️ O'rnatish va Ishga Tushirish

### 1. Python Muhitini Tayyorlash

Python 3.10 yoki undan yuqori versiyasi o'rnatilgan bo'lishi kerak.

Loyiha papkasida virtual muhit yarating va faollashtiring:

**Windows (PowerShell):**
```powershell
py -m venv venv
.\venv\Scripts\activate
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Kerakli kutubxonalarni o'rnating:
```bash
pip install -r requirements.txt
```

---

### 2. `.env` Faylini Sozlash

Loyiha ildizidagi `.env` faylida kalitlaringiz to'g'ri kiritilganligini tekshiring:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=@s_legenda_bot

DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_MODEL=deepseek-flash

# Ixtiyoriy zaxira (DeepSeek ishlamasa)
GLM_API_KEY=your_glm_api_key_here
GLM_MODELS=glm-4.7,glm-4.6

MEMES_DIR=Memes
MAX_CONTEXT_TOKENS=100000
CONTEXT_MESSAGES_LIMIT=8
AI_TEMPERATURE=0.55
AI_MAX_TOKENS=130
AI_FREQUENCY_PENALTY=0.5
AI_PRESENCE_PENALTY=0.3
ALLOWED_GROUP_ID=0
CREATOR_NAME=Muhammadaziz
CREATOR_USERNAME=@muhammadaziz
ADMIN_IDS=
```

---

### 3. Telegram BotFather Sozlamasi (Juda Muhim!)

Bot guruhdagi barcha xabarlarni ko'rishi va javob qaytarishi uchun Telegram BotFather'da **Group Privacy** rejimini o'chirish shart:

1. Telegram'da [@BotFather](https://t.me/BotFather) botiga kiring.
2. `/mybots` buyrug'ini yuboring va o'z botingizni tanlang.
3. **Bot Settings** -> **Group Privacy** bo'limiga kiring.
4. **Turn off** (yoki Disable) tugmasini bosing.
   *(Natija: `Privacy mode is disabled for ...` bo'lishi kerak).*
5. Shuningdek, bot guruhga qo'shilishi ruxsat etilgan bo'lishi kerak (**Bot Settings** -> **Allow Groups?** -> **Turn groups on**).

---

### 4. Sinovdan O'tkazish (Test)

Botning barcha modullarini ishga tushirishdan oldin avtomatik tekshirishingiz mumkin:

```bash
python tests/test_all.py
```

Ushbu test:
- API kalitlarini tekshiradi;
- Ma'lumotlar bazasini tekshiradi;
- `Memes` papkasidagi rasmlarni o'qiydi;
- AI ga savol berib javob oladi.

---

### 5. Botni Mahalliy Ishga Tushirish

Botni ishga tushirish:
```bash
python run.py
```

Endi botni o'z guruhingizga qo'shing va xabar yozing. Bot darhol o'zbek tilida muloqot qilishni boshlaydi.

---

## 🚀 Railway va VPS'da 24/7 ishlatish

### Railway'ga joylash

Railway loyihani GitHub repozitoriydan deploy qilganda ildizdagi `Dockerfile` avtomatik ishlatiladi. Bot polling rejimida bo'lgani uchun uni **bitta replica** bilan worker service sifatida ishlating; web port yoki public domain kerak emas.

1. Railway'da **New Project → Deploy from GitHub Repo** orqali repozitoriyani ulang.
2. Service Variables bo'limiga `TELEGRAM_BOT_TOKEN` va `DEEPSEEK_API_KEY` qiymatlarini kiriting. Kerak bo'lsa `ADMIN_IDS` va Tavily kalitlarini ham qo'shing. `DEEPSEEK_MODEL` kiritilmasa `deepseek-flash` ishlatiladi.
3. Service'ga Volume ulang va mount path'ni **`/app/data`** qiling. Bu SQLite bazasini va oxirgi profil rasmi indeksini redeploy/restart paytida saqlaydi.
4. Replica sonini `1` qiling va deploy loglarini kuzating. Ishga tushganda `Bot tayyor!` yozuvi chiqishi kerak.

Volume bo'lmasa Railway deploy vaqtida SQLite fayli yo'qolishi mumkin. `.env` faylini repozitoriyga yuklamang; maxfiy qiymatlarni Railway Variables orqali kiriting.

### Cloudflare Workers haqida

Loyiha hozir `aiogram` long polling (`dp.start_polling`) va lokal SQLite faylidan foydalanadi; shu sababli uni Cloudflare Workers/Pages'ga bevosita yuklab ishga tushirib bo'lmaydi. Workers uchun Telegram webhook va Cloudflare D1/KV kabi saqlash xizmatlariga moslashtirish kerak. Hozirgi kodni Railway'da qoldirib, Cloudflare'ni faqat DNS/proxy sifatida ishlatish mumkin.

### Systemd orqali Linux VPS'da ishlatish

Linux (Ubuntu/Debian) serverida botingiz to'xtovsiz ishlashi va server o'chib yonganda ham avtomatik qayta ishga tushishi uchun `legenda_bot.service` faylidan foydalaning.

1. Loyihani serverga yuklang (masalan, `/var/www/suhbatdosh-bot` papkasiga).
2. Serverda virtual muhit yaratib, kutubxonalarni o'rnating.
3. `legenda_bot.service` faylini tahrirlab, yo'llarni va foydalanuvchini moslang:
   ```bash
   nano legenda_bot.service
   ```
4. Faylni tizim papkasiga nusxalang:
   ```bash
   sudo cp legenda_bot.service /etc/systemd/system/
   ```
5. Servisni qayta yuklang va yoqing:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable legenda_bot
   sudo systemctl start legenda_bot
   ```
6. Servis holatini tekshirish:
   ```bash
   sudo systemctl status legenda_bot
   ```
7. Loglarni real vaqtda kuzatish:
    ```bash
    sudo journalctl -u legenda_bot -f
    ```

---

## 💬 Guruh Buyruqlari
- `/suhbat_boshlash` (yoki `/suhbat-boshlash`) — Bot faol muloqotni boshlaydi, o'zi gap boshlab guruh a'zolarini chaqiradi.
- `/stop_suhbatdosh` (yoki `/stop-suhbatdosh`) — Suhbatni to'xtatadi (bot faqat chaqirilganda javob beradi).
- `/clear` — Guruh suhbat tarixini tozalaydi.
- `/help` — Buyruqlar va qo'llanma.

## 🛠 Admin Buyruqlari

Agar `.env` faylida `ADMIN_IDS` ko'rsatilgan bo'lsa (masalan: `ADMIN_IDS=12345678`), quyidagi buyruqlar faol bo'ladi:

- `/update_avatar` — Profil rasmini qo'lda navbatdagisiga almashtirish.
- `/stats` — Bot statistikasi, oxirgi rasm indeksi va chatdagi faol tokenlar sonini ko'rish.
- `/chatid` — Joriy guruh/chat ID raqamini ko'rsatadi (`ALLOWED_GROUP_ID` sozlash uchun).
- `/clear` — Guruh suhbat xotirasini tozalash (istalgan foydalanuvchi ishlata oladi).

---

## 🤝 Murojaat va Qo'llab-quvvatlash
Barcha kodlar to'liq modulli qilib yozilgan. Qo'shimcha funksiyalar kerak bo'lsa, `src/handlers/group_chat.py` yoki `src/ai_service.py` fayllari orqali osongina kengaytirish mumkin!
