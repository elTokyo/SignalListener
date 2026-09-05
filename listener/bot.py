"""
Точка входа: запускает Telegram-бота + Discord-listener в фоновом потоке.

ВАЖНО: этот бот использует py-cord (форк discord.py) для voice receive.
В requirements.txt должен быть py-cord, а НЕ discord.py.
"""
import logging
import threading
import asyncio
import aiohttp
from telegram.ext import Application, CommandHandler

import config
import handlers
import voice_listener

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def start_discord_in_background():
    if not config.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN не задан — Discord-бот не запустится")
        return

    def runner():
        try:
            voice_listener.run_discord_bot()
        except Exception as e:
            logger.exception(f"Discord crashed: {e}")

    t = threading.Thread(target=runner, daemon=True, name="discord")
    t.start()


def make_telegram_sender(app: Application):
    """
    Возвращает async-функцию которая шлёт текст админу в Telegram.
    Используется voice_listener для отправки транскрипций.
    """
    async def send(text: str):
        if not config.ADMIN_CHAT_ID:
            logger.error("ADMIN_CHAT_ID не задан")
            return
        try:
            await app.bot.send_message(
                chat_id=config.ADMIN_CHAT_ID,
                text=f"🎙 {text}",
            )
        except Exception as e:
            logger.error(f"TG send failed: {e}")
    return send


def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан")
    if not config.ADMIN_CHAT_ID:
        logger.warning("ADMIN_CHAT_ID не задан — транскрипции некуда слать!")
    if not config.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY не задан — Whisper не будет работать!")

    app = Application.builder().token(config.BOT_TOKEN).build()

    # Регистрируем функцию отправки в Telegram у voice_listener
    voice_listener.set_telegram_sender(make_telegram_sender(app))

    app.add_handler(CommandHandler("start",   handlers.cmd_start))
    app.add_handler(CommandHandler("listen",  handlers.cmd_listen))
    app.add_handler(CommandHandler("stop",    handlers.cmd_stop))
    app.add_handler(CommandHandler("status",  handlers.cmd_status))

    start_discord_in_background()

    logger.info("Telegram-бот запущен")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
