# Voice Test Bot

Тестовый бот: слушает админа в голосовом канале Discord и шлёт транскрипты в Telegram.

## Что делает

1. `/listen` — бот заходит в указанный голосовой канал Discord
2. Слушает только указанного пользователя (админа DC), остальных игнорирует
3. Когда админ говорит и потом замолкает (~1.5 сек тишины) — отправляет накопленный кусок в OpenAI Whisper
4. Распознанный текст шлёт админу в Telegram
5. `/stop` — выйти из канала

## Зависимости

- `py-cord` — форк discord.py с поддержкой voice receive (стандартный discord.py НЕ умеет принимать аудио)
- `PyNaCl` — обязательно для voice
- `python-telegram-bot` — для Telegram

## Подготовка

### 1. Discord-бот

Это **отдельный** бот, не тот что используется в основном signal-bot.

1. https://discord.com/developers/applications → New Application
2. Bot → Add Bot, скопировать TOKEN
3. **Bot intents**: включить `SERVER MEMBERS INTENT` и `VOICE_STATES` (последний включён по умолчанию)
4. OAuth2 → URL Generator → scope `bot`, permissions: `Connect`, `Speak`, `Use Voice Activity`, `View Channels`
5. Добавить бота на сервер по сгенерированной ссылке
6. Дать боту доступ к нужному голосовому каналу

### 2. ID голосового канала

В Discord включить Developer Mode (Settings → Advanced → Developer Mode), затем правый клик на голосовой канал → Copy Channel ID.

### 3. OpenAI API ключ

1. https://platform.openai.com/ → Sign up
2. Пополнить баланс ($5 минимум через карту)
3. API Keys → Create new secret key
4. Скопировать ключ (показывается один раз!)

**Стоимость:** Whisper API — $0.006 за минуту аудио. Часовая сессия ≈ $0.36.

### 4. Telegram-бот

Это **отдельный** Telegram-бот, не основной.

1. @BotFather → /newbot → создать
2. Скопировать токен
3. Узнать свой Telegram user_id: @userinfobot → /start

## Переменные окружения

```
BOT_TOKEN=<токен telegram-бота>
ADMIN_CHAT_ID=<твой telegram user_id>
DISCORD_TOKEN=<токен discord-бота>
DISCORD_VOICE_CHANNEL_ID=<ID голосового канала>
DISCORD_ADMIN_USER_ID=784124183223205950
OPENAI_API_KEY=<sk-...>
```

`DISCORD_ADMIN_USER_ID` уже зашит как дефолт (твой), можно не задавать.

## Деплой на Railway

1. Создать новый проект, подключить GitHub-репо с этим кодом
2. **Variables** → добавить все переменные выше
3. **Replicas: 1** (один регион, одна реплика)
4. Деплой пойдёт автоматически

## Использование

1. В Telegram написать боту `/listen`
2. Бот зайдёт в голосовой канал
3. Ты говоришь в этом канале — через ~1.5 сек после паузы получаешь транскрипт в ТГ
4. `/stop` чтобы выйти

## Возможные проблемы

**"Не подключился: missing access"**
Бот не имеет прав в голосовом канале. Дать роль с правами Connect+Speak.

**Транскрипты не приходят**
- Проверь логи: есть ли `Чанк готов`? Если нет — Discord не отдаёт аудио (проверь intents и права).
- Если `Чанк готов` есть, но `Whisper вернул пусто` — проверь OPENAI_API_KEY и баланс.

**"Уже подключён"**
Бот уже в канале. Сделай `/stop` сначала, потом `/listen` заново.

## Файлы

- `bot.py` — точка входа
- `config.py` — переменные окружения
- `handlers.py` — Telegram-команды
- `voice_listener.py` — Discord voice receive через py-cord Sink
- `audio_buffer.py` — буферизация PCM, детект тишины, конвертация в WAV
- `whisper_client.py` — клиент OpenAI Whisper API
- `requirements.txt`, `Dockerfile`
