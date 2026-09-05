"""
Telegram-команды для управления voice-ботом.

/start — приветствие
/listen — зайти в голосовой канал и начать слушать
/stop — отключиться
/status — статус
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

import config
import voice_listener

logger = logging.getLogger(__name__)


def _is_admin(update: Update) -> bool:
    return update.effective_user.id == config.ADMIN_CHAT_ID


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("⛔ Этот бот только для админа.")
        return
    await update.message.reply_text(
        "🎙 Voice-тест бот\n\n"
        "/listen — зайти в голосовой канал и слушать админа\n"
        "/stop — отключиться\n"
        "/status — статус\n\n"
        "Транскрипты будут приходить сюда."
    )


async def cmd_listen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    msg = await update.message.reply_text("🔄 Подключаюсь к голосовому каналу...")
    ok, info = voice_listener.trigger_start()
    icon = "✅" if ok else "❌"
    await msg.edit_text(f"{icon} {info}")


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    msg = await update.message.reply_text("🔄 Отключаюсь...")
    ok, info = voice_listener.trigger_stop()
    icon = "✅" if ok else "❌"
    await msg.edit_text(f"{icon} {info}")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    status = "🟢 Слушаю" if voice_listener.is_listening() else "⚪️ Не подключён"
    await update.message.reply_text(
        f"{status}\n"
        f"Канал ID: {config.DISCORD_VOICE_CHANNEL_ID}\n"
        f"Админ DC user_id: {config.DISCORD_ADMIN_USER_ID}"
    )
