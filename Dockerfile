# FROM python:3.11-slim

# # Add non-free repositories for Intel drivers
# RUN echo "deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
#     echo "deb http://deb.debian.org/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# RUN apt-get update && apt-get install -y \
#     ffmpeg \
#     imagemagick \
#     libsm6 \
#     libxext6 \
#     libxrender-dev \
#     libgomp1 \
#     fonts-dejavu-core \
#     pkg-config \
#     libavcodec-dev \
#     libavformat-dev \
#     libavutil-dev \
#     libavdevice-dev \
#     libavfilter-dev \
#     libswscale-dev \
#     libswresample-dev \
#     gcc \
#     g++ \
#     make \
#     wget \
#     unzip \
#     fontconfig \
#     intel-media-va-driver \
#     vainfo \
#     libva2 \
#     libva-drm2 \
#     && rm -rf /var/lib/apt/lists/*

# # Install Montserrat font
# RUN wget https://github.com/JulietaUla/Montserrat/archive/refs/heads/master.zip -O /tmp/montserrat.zip \
#     && unzip /tmp/montserrat.zip -d /tmp \
#     && mkdir -p /usr/share/fonts/truetype/montserrat \
#     && find /tmp/Montserrat-master -name "*.ttf" -exec cp {} /usr/share/fonts/truetype/montserrat/ \; \
#     && fc-cache -f -v \
#     && rm -rf /tmp/montserrat.zip /tmp/Montserrat-master

# # Fix ImageMagick policy
# RUN sed -i 's/rights="none" pattern="@\\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml || \
#     sed -i 's/rights="none" pattern="@\\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick*/policy.xml || true

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY app/ ./app/

# RUN mkdir -p /app/output /app/cache /app/logs

# EXPOSE 8501

# CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]


FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    libsm6 \
    libxext6 \
    libxrender-dev \
    fonts-dejavu-core \
    libgomp1 \
    wget \
    vainfo \
    intel-media-va-driver-non-free \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p cache output logs

# Expose ports
EXPOSE 8000 8501

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]