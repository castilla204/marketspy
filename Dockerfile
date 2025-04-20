# Usa una imagen base oficial de Python
FROM python:3.11-slim

# Instalar dependencias del sistema necesarias para Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Instalar Chromium
RUN apt-get update && apt-get install -y chromium \
    && rm -rf /var/lib/apt/lists/*

# Verificar la versión de Chromium instalada
RUN chromium --version

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de requisitos
COPY requirements.txt ./

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el script principal
COPY app.py .

# Documenta el puerto que usa la aplicación
EXPOSE 7000

# Comando para ejecutar la aplicación con Uvicorn
CMD ["xvfb-run", "--auto-servernum", "chromium", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--headless", "--remote-debugging-port=9222", "&", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7000"]
