"""
Распознавание речи через OpenAI Whisper API.
Принимает аудио (WAV bytes), возвращает распознанный текст.
"""
import logging
import io
import aiohttp

import config

logger = logging.getLogger(__name__)

WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"


async def transcribe(wav_bytes: bytes) -> str:
    """
    Отправляет WAV-аудио в Whisper API, возвращает распознанный текст.
    При ошибке возвращает пустую строку.
    """
    if not config.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY не задан")
        return ""

    if not wav_bytes:
        return ""

    headers = {"Authorization": f"Bearer {config.OPENAI_API_KEY}"}

    data = aiohttp.FormData()
    data.add_field("file", io.BytesIO(wav_bytes),
                   filename="audio.wav", content_type="audio/wav")
    data.add_field("model", config.WHISPER_MODEL)
    if config.WHISPER_LANGUAGE:
        data.add_field("language", config.WHISPER_LANGUAGE)
    data.add_field("response_format", "text")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WHISPER_URL, headers=headers, data=data, timeout=60
            ) as resp:
                text = (await resp.text()).strip()
                if resp.status != 200:
                    logger.error(f"Whisper API {resp.status}: {text[:200]}")
                    return ""
                return text
    except Exception as e:
        logger.error(f"Whisper transcribe error: {e}")
        return ""
