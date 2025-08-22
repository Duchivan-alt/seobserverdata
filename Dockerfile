# Étape de construction
FROM python:3.11-slim-bullseye as builder

# Installer les dépendances système nécessaires pour la construction
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Créer un environnement virtuel
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Étape de production
FROM python:3.11-slim-bullseye

# Définir les variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Installer les dépendances système et Google Chrome
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dépendances système de base
    libgomp1 \
    libglib2.0-0 \
    libnss3 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    libxtst6 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libpango-1.0-0 \
    xdg-utils \
    xvfb \
    # Outils pour installer Chrome
    wget \
    gnupg \
    ca-certificates \
    # Ajout du repo et installation de Chrome
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    # Nettoyage
    && rm -rf /var/lib/apt/lists/*

# Copier l'environnement virtuel depuis le builder
COPY --from=builder /opt/venv /opt/venv

# Créer et définir le répertoire de travail
WORKDIR /app

# Copier uniquement les fichiers nécessaires
COPY app.py .
COPY requirements.txt .
COPY templates/ ./templates/
COPY static/ ./static/

# Créer un utilisateur non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

# Exposer le port
EXPOSE $PORT

# Commande de démarrage
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "300", "app:app"]
