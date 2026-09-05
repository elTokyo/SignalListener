"""
Discord voice listener на py-cord.

py-cord использует "Sink" API для приёма аудио: бот заходит в голосовой канал
через VoiceClient, начинает запись через voice_client.start_recording(sink, ...),
и для каждого говорящего пользователя в sink.write() приходят PCM-фреймы.

Здесь мы:
1. Принимаем фреймы только от ADMIN_USER_ID, остальных игнорируем.
2. Буферизуем через UserAudioBuffer.
3. При готовности чанка → Whisper → Telegram.
"""
import asyncio
import logging
import threading
from typing import Optional

import discord
from discord.sinks import Sink, default_filters, Filters

import config
from audio_buffer import UserAudioBuffer
import whisper_client

logger = logging.getLogger(__name__)

# Глобальные ссылки на клиента и его loop — нужны чтобы команды /listen из
# Telegram-потока могли управлять voice-клиентом в его asyncio-loop.
_bot: Optional[discord.Bot] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_voice_client: Optional[discord.VoiceClient] = None
_active_buffer: Optional[UserAudioBuffer] = None
_telegram_sender = None  # async callable(text) — устанавливается извне


class AdminSink(Sink):
    """
    Кастомный Sink: пропускает PCM только от админа в его UserAudioBuffer.
    Остальных пользователей игнорирует.
    """

    def __init__(self, buffer: UserAudioBuffer):
        # filters=None отключает фильтрацию (берём всё, фильтр по user_id вручную)
        super().__init__()
        self.encoding = "pcm"
        self.vc = None
        self.audio_data = {}
        self._buffer = buffer

    @Filters.container
    def write(self, data: bytes, user: int):
        # data — сырое PCM (после декодирования Opus): 48kHz/16bit/stereo
        # user — Discord user_id говорящего
        if user != config.DISCORD_ADMIN_USER_ID:
            return
        try:
            self._buffer.feed(data)
        except Exception as e:
            logger.exception(f"AdminSink.write error: {e}")

    def cleanup(self):
        pass

    def format_audio(self, audio):
        # Не используется (мы не сохраняем файлы)
        pass


async def _on_chunk_ready(wav_bytes: bytes, duration: float):
    """Колбэк когда буфер собрал готовый кусок: транскрибируем и шлём в Telegram."""
    logger.info(f"Чанк готов: {duration:.1f}с, отправка в Whisper")
    text = await whisper_client.transcribe(wav_bytes)
    if not text:
        logger.info("Whisper вернул пусто")
        return
    logger.info(f"Транскрибировано ({duration:.1f}с): {text[:80]}")
    if _telegram_sender:
        try:
            await _telegram_sender(text)
        except Exception as e:
            logger.exception(f"Telegram send error: {e}")


def set_telegram_sender(fn):
    """Регистрирует async-функцию которая будет слать текст в Telegram."""
    global _telegram_sender
    _telegram_sender = fn


# ── API для управления из Telegram-команд ────────────────────────────────────

async def start_listening_async() -> tuple[bool, str]:
    """Подключиться к голосовому каналу и начать запись."""
    global _voice_client, _active_buffer

    if _voice_client and _voice_client.is_connected():
        return False, "Уже подключён к голосовому каналу"

    if not _bot:
        return False, "Discord-бот ещё не запустился"

    channel = _bot.get_channel(config.DISCORD_VOICE_CHANNEL_ID)
    if channel is None:
        return False, f"Канал {config.DISCORD_VOICE_CHANNEL_ID} не найден"
    if not isinstance(channel, discord.VoiceChannel):
        return False, "Указанный канал не голосовой"

    try:
        _voice_client = await channel.connect()
    except Exception as e:
        logger.exception(f"connect error: {e}")
        return False, f"Ошибка подключения: {e}"

    # Создаём буфер для админа и Sink
    _active_buffer = UserAudioBuffer(
        user_id=config.DISCORD_ADMIN_USER_ID,
        on_chunk_ready=_on_chunk_ready,
        loop=_loop,
    )
    _active_buffer.start_watcher()

    sink = AdminSink(_active_buffer)

    def _stop_callback(sink, *args):
        # Колбэк вызывается py-cord когда запись остановлена. Ничего особенного.
        logger.info("Recording finished callback")

    try:
        _voice_client.start_recording(sink, _stop_callback)
    except Exception as e:
        logger.exception(f"start_recording error: {e}")
        try:
            await _voice_client.disconnect()
        except Exception:
            pass
        _voice_client = None
        _active_buffer = None
        return False, f"Не удалось начать запись: {e}"

    logger.info(f"Слушаю канал {channel.name}, админ user_id={config.DISCORD_ADMIN_USER_ID}")
    return True, f"Подключился к «{channel.name}», слушаю админа"


async def stop_listening_async() -> tuple[bool, str]:
    """Остановить запись и выйти из канала."""
    global _voice_client, _active_buffer

    if not _voice_client or not _voice_client.is_connected():
        return False, "Не подключён к голосовому каналу"

    try:
        _voice_client.stop_recording()
    except Exception as e:
        logger.warning(f"stop_recording: {e}")

    if _active_buffer:
        await _active_buffer.stop()
        _active_buffer = None

    try:
        await _voice_client.disconnect()
    except Exception as e:
        logger.warning(f"disconnect: {e}")
    _voice_client = None

    return True, "Отключился от голосового канала"


def trigger_start() -> tuple[bool, str]:
    """Вызывается из Telegram-потока. Планирует start в loop Discord-бота."""
    if _loop is None:
        return False, "Discord ещё не запустился"
    fut = asyncio.run_coroutine_threadsafe(start_listening_async(), _loop)
    try:
        return fut.result(timeout=30)
    except Exception as e:
        return False, f"Timeout/Error: {e}"


def trigger_stop() -> tuple[bool, str]:
    if _loop is None:
        return False, "Discord ещё не запустился"
    fut = asyncio.run_coroutine_threadsafe(stop_listening_async(), _loop)
    try:
        return fut.result(timeout=30)
    except Exception as e:
        return False, f"Timeout/Error: {e}"


def is_listening() -> bool:
    return bool(_voice_client and _voice_client.is_connected())


# ── Запуск Discord-бота ──────────────────────────────────────────────────────

def run_discord_bot():
    """Блокирующий вызов, запускает discord.Bot в текущем потоке."""
    global _bot, _loop

    intents = discord.Intents.default()
    intents.voice_states = True
    intents.message_content = False  # текст не парсим в этом боте

    bot = discord.Bot(intents=intents)
    _bot = bot

    @bot.event
    async def on_ready():
        global _loop
        _loop = asyncio.get_running_loop()
        logger.info(f"Discord готов: {bot.user} (id={bot.user.id})")

    bot.run(config.DISCORD_TOKEN)
