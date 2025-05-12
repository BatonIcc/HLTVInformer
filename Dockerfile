FROM python:3.10.13-slim-bookworm

RUN apt-get update && \
    apt-get install -y \
    wget \
    gnupg2 \
    libgtk-3-0 \
    libnotify-dev \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libxtst6 \
    xauth \
    xvfb \
    fonts-liberation \
    libappindicator3-1 \
    libnspr4 \
    libdrm2 \
    libgbm1 \
    libxshmfence1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium \
    && playwright install-deps

COPY . .

RUN mkdir -p /app/data /app/logs \
    && chmod -R 777 /app/data /app/logs

CMD ["python", "main.py"]