FROM python:3.11-slim

# Системные зависимости:
# - libopus0: декодирование Opus (Discord использует Opus для голоса)
# - ffmpeg: на всякий случай для аудио-операций
# - gcc/build-essential: для сборки PyNaCl если colesa колеса не подойдут
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopus0 \
    libopus-dev \
    libffi-dev \
    libssl-dev \
    ffmpeg \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
