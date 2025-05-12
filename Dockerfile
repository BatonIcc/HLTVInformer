# Используем официальный образ Python
FROM python:3.10.1-slim-buster

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы
COPY . .

# Создаем директории для данных и логов
RUN mkdir -p /app/data /app/logs

# Команда для запуска бота
CMD ["python", "bot.py"]