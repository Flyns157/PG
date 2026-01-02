"""
Point d'entrée principal de l'application FastAPI.

Ce fichier configure et lance l'application FastAPI avec tous les composants
nécessaires : CORS, documentation, routeurs, et gestion des erreurs.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.database.session import engine, Base
from app.routers import auth, passwords


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie de l'application.
    Crée les tables de la base de données au démarrage.
    """
    # Création des tables au démarrage
    Base.metadata.create_all(bind=engine)
    yield
    # Nettoyage éventuel à l'arrêt
    pass


# Création de l'application FastAPI
app = FastAPI(
    title="API de Gestion de Mots de Passe",
    description="""
    Une API sécurisée pour la gestion de vos mots de passe.
    
    ## Fonctionnalités
    
    - **Authentification** : Inscription et connexion sécurisées avec JWT
    - **Gestion des mots de passe** : CRUD complet pour organiser vos identifiants
    - **Sécurité** : Hachage bcrypt et tokens JWT avec expiration
    - **Isolation des données** : Chaque utilisateur accède uniquement à ses propres mots de passe
    
    ## Authentification
    
    Tous les endpoints de gestion des mots de passe nécessitent une authentification.
    Utilisez le endpoint `/auth/login` pour obtenir un token JWT, puis incluez-le
    dans le header `Authorization` : `Bearer <token>`
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuration des gestionnaires d'exceptions
setup_exception_handlers(app)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routeurs avec préfixe d'API
app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["Authentification"])
app.include_router(passwords.router, prefix=settings.API_V1_PREFIX, tags=["Mots de passe"])


@app.get("/", tags=["Santé"])
async def root():
    """
    Endpoint de vérification de l'état de l'API.
    
    Retourne un message de bienvenue et l'état de l'API.
    """
    return {
        "message": "Bienvenue sur l'API de Gestion de Mots de Passe",
        "version": "1.0.0",
        "documentation": "/docs",
    }


@app.get("/health", tags=["Santé"])
async def health_check():
    """
    Endpoint de vérification de l'état de santé de l'API.
    
    Utilisé par les systèmes de monitoring pour vérifier que l'application
    fonctionne correctement.
    """
    return {"status": "healthy", "service": "password-manager-api"}
