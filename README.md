# API de Gestion de Mots de Passe

Une API RESTful sécurisée pour la gestion de vos mots de passe, construite avec FastAPI, SQLAlchemy et Pydantic.

## Fonctionnalites

- Authentification JWT avec tokens a expiration
- Hachage bcrypt pour les mots de passe utilisateur
- CRUD complet pour les entrees de mots de passe
- Isolation des donnees par utilisateur
- Documentation automatique avec Swagger UI

## Prerequis

- Python 3.13+
- Docker (optionnel)

## Installation Locale

```bash
# Creation de l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installation des dependances
pip install -r requirements.txt

# Lancement du serveur
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Installation avec Docker

```bash
# Construction de l'image
docker build -t password-manager:latest .

# Lancement du conteneur
docker run -d -p 8000:8000 --name pm-api password-manager:latest
```

## Endpoints

| Methode | Endpoint               | Description               |
| ------- | ---------------------- | ------------------------- |
| POST    | /api/v1/auth/signup    | Inscription               |
| POST    | /api/v1/auth/login     | Connexion                 |
| GET     | /api/v1/passwords/     | Liste des mots de passe   |
| POST    | /api/v1/passwords/     | Creer un mot de passe     |
| GET     | /api/v1/passwords/{id} | Recuperer un mot de passe |
| PUT     | /api/v1/passwords/{id} | Modifier un mot de passe  |
| DELETE  | /api/v1/passwords/{id} | Supprimer un mot de passe |

## Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

Le fichier `.env` contient les variables de configuration :

```env
DATABASE_URL=sqlite:///./password_manager.db
SECRET_KEY=votre_cle_secrete
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Structure du Projet

```
password_manager/
├── app/
│   ├── core/          # Configuration et securite
│   ├── database/      # Session SQLAlchemy
│   ├── models/        # Models de donnees
│   ├── routers/       # Endpoints API
│   ├── schemas/       # Validation Pydantic
│   └── services/      # Logique metier
├── tests/
├── Dockerfile
├── requirements.txt
└── .env
```

## Lancer les Tests

```bash
# Installation des dependances de test
pip install pytest pytest-cov httpx

# Lancer tous les tests
pytest tests/ -v

# Lancer avec coverage
pytest --cov=app --cov-report=term-missing tests/

# Lancer une categorie specifique
pytest tests/test_api/ -v
pytest tests/test_unit/test_security.py -v
```

## E

## Licence

MIT
