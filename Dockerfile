# =============================================================================
# Dockerfile optimisé pour l'API de gestion de mots de passe
# Objectif: Image Docker la plus légère possible avec Python 3.13
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Installation des dépendances
# -----------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS builder

# Variables d'environnement pour optimiser le build
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Répertoire de travail
WORKDIR /build

# Installation des dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie des fichiers de configuration
COPY requirements.txt .

# Installation des dépendances Python dans un répertoire isolé
RUN pip install --prefix=/install -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Production - Image finale légère
# -----------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS production

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Création d'un utilisateur non-root pour la sécurité
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Répertoire de travail
WORKDIR /home/appuser

# Copie uniquement les dépendances installées depuis le builder
COPY --from=builder /install /usr/local

# Copie le code de l'application
COPY --chown=appuser:appgroup . .

# Changement vers l'utilisateur non-root
USER appuser

# Exposition du port
EXPOSE 8000

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
