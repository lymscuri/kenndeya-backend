# Dockerfile pour Kendeya Backend
# Image multi-stage pour optimiser la taille de l'image finale

# Stage 1: Builder
FROM python:3.11-slim as builder

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installer les dépendances système nécessaires pour les packages Python
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Créer un répertoire pour l'application
WORKDIR /app

# Copier les fichiers de requirements
COPY requirements/ /app/requirements/

# Installer les dépendances Python
RUN pip install --upgrade pip && \
    pip install -r requirements/production.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

# Installer les dépendances système runtime
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root pour exécuter l'application
RUN useradd -m -u 1000 kendeya && \
    mkdir -p /app /app/staticfiles /app/media && \
    chown -R kendeya:kendeya /app

# Définir le répertoire de travail
WORKDIR /app

# Copier les dépendances Python installées depuis le builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copier le code de l'application
COPY --chown=kendeya:kendeya . /app/

# Passer à l'utilisateur non-root
USER kendeya

# Collecter les fichiers statiques
RUN python manage.py collectstatic --noinput || true

# Exposer le port 8000
EXPOSE 8000

# Commande par défaut (peut être surchargée dans docker-compose)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
