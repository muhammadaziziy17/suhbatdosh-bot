import os
from pathlib import Path
from dotenv import load_dotenv

# Loyihaning asosiy papkasi (root)
BASE_DIR = Path(__file__).resolve().parent.parent

# .env faylini yuklash
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Telegram Bot sozlamalari
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "").strip()

# DeepSeek API sozlamalari
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip()

# Ixtiyoriy GLM zaxira modellari
GLM_API_KEY = os.getenv("GLM_API_KEY", "").strip()
_raw_glm_models = os.getenv("GLM_MODELS", "glm-4.7,glm-4.6")
GLM_FALLBACK_MODELS = [m.strip() for m in _raw_glm_models.split(",") if m.strip()]

# Tavily qidiruv API kaliti (internetdan faktik ma'lumot olish uchun)
TAVILY_API_KEY = (os.getenv("TAVILY_API_KEY_1", "").strip() or os.getenv("TAVILY_API_KEY_2", "").strip())


# Rasmlar papkasi (Memes yoki memes)
MEMES_DIR_NAME = os.getenv("MEMES_DIR", "Memes")
MEMES_DIR = BASE_DIR / MEMES_DIR_NAME
if not MEMES_DIR.exists():
    # Agar katta-kichik harflar tufayli topilmasa, tekshirish
    lower_memes = BASE_DIR / "memes"
    if lower_memes.exists():
        MEMES_DIR = lower_memes

# Ma'lumotlar bazasi yo'li
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "bot_database.sqlite3"

# Kontekst va xotira chegaralari
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "100000"))
# AI ga kontekst sifatida beriladigan oxirgi xabarlar soni (6-8 oralig'ida ushlanadi)
CONTEXT_MESSAGES_LIMIT = int(os.getenv("CONTEXT_MESSAGES_LIMIT", "8"))

# AI API chaqiruv parametrlari (qisqa, xilma-xil va takrorsiz javoblar uchun qat'iy cheklov)
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.55"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "130"))
AI_FREQUENCY_PENALTY = float(os.getenv("AI_FREQUENCY_PENALTY", "0.5"))
AI_PRESENCE_PENALTY = float(os.getenv("AI_PRESENCE_PENALTY", "0.3"))

# Adminlar ro'yxati
_raw_admins = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = [int(a.strip()) for a in _raw_admins.split(",") if a.strip().isdigit()]

# Validatsiya
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi! Iltimos, .env faylini to'ldiring.")

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY topilmadi! Iltimos, .env fayliga DeepSeek API kalitini kiriting.")
