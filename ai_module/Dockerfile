FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Создаём только директории (код придёт через volume)
RUN mkdir -p cache/ai_images output

EXPOSE 8502

# Hot reload включён по умолчанию в Streamlit
CMD ["streamlit", "run", "app.py", \
     "--server.port", "8502", \
     "--server.address", "0.0.0.0", \
     "--server.fileWatcherType", "auto", \
     "--server.runOnSave", "true"]
