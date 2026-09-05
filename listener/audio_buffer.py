"""
Буферизация аудио от одного пользователя Discord.

Discord даёт PCM 48000 Hz, 16-bit, stereo (через py-cord voice receive).
Накапливаем PCM, отслеживаем тишину, при паузе или превышении лимита —
конвертируем в WAV и отдаём на распознавание.
"""
import io
import time
import wave
import asyncio
import logging
from typing import Callable, Awaitable, Optional

import config

logger = logging.getLogger(__name__)

# Параметры PCM от Discord/py-cord
SAMPLE_RATE = 48000
SAMPLE_WIDTH = 2      # bytes per sample (16-bit)
CHANNELS = 2

# Сколько байт PCM в одной секунде
BYTES_PER_SEC = SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS


def pcm_to_wav(pcm: bytes) -> bytes:
    """Заворачивает сырое PCM в WAV-контейнер."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(CHANNELS)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    return buf.getvalue()


class UserAudioBuffer:
    """
    Буфер для одного пользователя.
    on_chunk_ready(wav_bytes, duration_sec) — async callback, вызывается когда чанк готов.
    """

    def __init__(self,
                 user_id: int,
                 on_chunk_ready: Callable[[bytes, float], Awaitable[None]],
                 loop: asyncio.AbstractEventLoop):
        self.user_id = user_id
        self.on_chunk_ready = on_chunk_ready
        self.loop = loop

        self._pcm = bytearray()
        self._last_audio_ts: Optional[float] = None    # время последнего непустого пакета
        self._chunk_started_ts: Optional[float] = None # время начала текущего чанка
        self._flush_lock = asyncio.Lock()
        self._watcher_task: Optional[asyncio.Task] = None
        self._stopped = False

    def feed(self, pcm_data: bytes):
        """
        Добавить PCM-данные пользователя. Вызывается из voice receive callback.
        Может вызываться из НЕ-asyncio потока, поэтому только append, без async.
        """
        if self._stopped or not pcm_data:
            return
        now = time.monotonic()
        if self._chunk_started_ts is None:
            self._chunk_started_ts = now
        self._last_audio_ts = now
        self._pcm.extend(pcm_data)

    def start_watcher(self):
        """Запускает фоновую задачу которая отслеживает тишину и переполнение."""
        if self._watcher_task is None or self._watcher_task.done():
            self._watcher_task = asyncio.run_coroutine_threadsafe(
                self._watch(), self.loop
            )

    async def _watch(self):
        """Каждые 200мс проверяет: была ли тишина или превышен лимит чанка."""
        while not self._stopped:
            await asyncio.sleep(0.2)
            await self._maybe_flush()

    async def _maybe_flush(self):
        if not self._pcm or self._last_audio_ts is None:
            return
        now = time.monotonic()
        silence = now - self._last_audio_ts
        chunk_age = (now - self._chunk_started_ts) if self._chunk_started_ts else 0

        should_flush = (
            silence >= config.SILENCE_TIMEOUT_SEC
            or chunk_age >= config.MAX_CHUNK_SEC
        )
        if not should_flush:
            return

        async with self._flush_lock:
            if not self._pcm:
                return
            pcm = bytes(self._pcm)
            self._pcm = bytearray()
            self._chunk_started_ts = None
            self._last_audio_ts = None

        duration = len(pcm) / BYTES_PER_SEC
        if duration < config.MIN_CHUNK_SEC:
            logger.debug(f"Слишком короткий чанк ({duration:.2f}с), пропускаем")
            return

        try:
            wav = pcm_to_wav(pcm)
            await self.on_chunk_ready(wav, duration)
        except Exception as e:
            logger.exception(f"on_chunk_ready error: {e}")

    async def stop(self):
        """Остановить буфер, флашнуть остаток."""
        self._stopped = True
        await self._maybe_flush()
