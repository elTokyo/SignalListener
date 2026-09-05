"""Конфигурация тестового voice-бота."""
import os

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# Кому слать транскрипты (твой Telegram user_id)
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
# ID голосового канала который слушаем
DISCORD_VOICE_CHANNEL_ID = int(os.getenv("DISCORD_VOICE_CHANNEL_ID", "0"))
# ID пользователя чью речь транскрибируем (админ DC). Остальных игнорируем.
DISCORD_ADMIN_USER_ID = int(os.getenv("DISCORD_ADMIN_USER_ID", "784124183223205950"))

# OpenAI Whisper API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
WHISPER_MODEL = "whisper-1"
WHISPER_LANGUAGE = "ru"  # ускоряет и улучшает распознавание русского

# Параметры буферизации аудио
# Если админ молчит дольше SILENCE_TIMEOUT_SEC — отправляем накопленный кусок на распознавание
SILENCE_TIMEOUT_SEC = 1.5
# Принудительно отправлять на распознавание каждые MAX_CHUNK_SEC секунд (если говорит без пауз)
MAX_CHUNK_SEC = 30
# Минимальная длина куска для отправки (защита от обрывков)
MIN_CHUNK_SEC = 0.5
