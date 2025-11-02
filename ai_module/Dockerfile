FROM python:3.11-slim

WORKDIR /app

# Устанавливаем watchdog для отслеживания изменений
RUN pip install --no-cache-dir watchdog

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Создаём только директории (код придёт через volume)
RUN mkdir -p cache/ai_images output ai_services

EXPOSE 8502

# Hot reload с агрессивным отслеживанием изменений
CMD ["streamlit", "run", "app.py", \
     "--server.port", "8502", \
     "--server.address", "0.0.0.0", \
     "--server.fileWatcherType", "watchdog", \
     "--server.runOnSave", "true", \
     "--server.allowRunOnSave", "true", \
     "--browser.gatherUsageStats", "false"]