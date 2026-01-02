"""
Gestionnaires d'exceptions personnalisés pour l'API.

Ce module définit les exceptions personnalisées et leurs gestionnaires
pour fournir des réponses d'erreur cohérentes et informatives.
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class HTTPExceptionWithDetail(HTTPException):
    """
    Exception HTTP avec un message de détail personnalisé.

    Étend la classe HTTPException standard pour inclure un message
    plus informatif dans les réponses d'erreur.
    """

    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.detail = detail


class CredentialsException(HTTPExceptionWithDetail):
    """
    Exception pour les erreurs d'authentification.

    Utilisée lorsque les informations d'identification sont invalides
    ou le token est expiré.
    """

    def __init__(self, detail: str = "Impossible de valider les identifiants"):
        super().__init__(status_code=401, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


class NotFoundException(HTTPExceptionWithDetail):
    """
    Exception pour les ressources non trouvées.

    Utilisée lorsqu'une ressource demandée n'existe pas ou
    l'utilisateur n'a pas le droit d'y accéder.
    """

    def __init__(self, detail: str = "Ressource non trouvée"):
        super().__init__(status_code=404, detail=detail)


class ForbiddenException(HTTPExceptionWithDetail):
    """
    Exception pour les accès interdits.

    Utilisée lorsqu'un utilisateur essaie d'accéder à une ressource
    qui ne lui appartient pas.
    """

    def __init__(self, detail: str = "Accès interdit"):
        super().__init__(status_code=403, detail=detail)


class ConflictException(HTTPExceptionWithDetail):
    """
    Exception pour les conflits de ressources.

    Utilisée lors d'une tentative de création d'une ressource
    qui existe déjà (par exemple, un email déjà utilisé).
    """

    def __init__(self, detail: str = "Conflit de ressource"):
        super().__init__(status_code=409, detail=detail)


async def http_exception_handler(request: Request, exc: HTTPExceptionWithDetail):
    """
    Gestionnaire global pour les exceptions HTTP personnalisées.

    Formate les réponses d'erreur de manière cohérente.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "path": request.url.path,
            }
        },
        headers=exc.headers,
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    Gestionnaire générique pour toutes les autres exceptions.

    Fournit une réponse d'erreur cohérente pour les exceptions non gérées.
    """
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Une erreur interne s'est produite",
                "path": request.url.path,
            }
        },
    )


def setup_exception_handlers(app):
    """
    Configure tous les gestionnaires d'exceptions pour l'application.

    Args:
        app: L'instance FastAPI à configurer.
    """
    app.add_exception_handler(HTTPExceptionWithDetail, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
