class DomainError(Exception):
    """Erreur métier, traduite en réponse HTTP par app.api.errors."""

    message = "Erreur métier"

    def __init__(self) -> None:
        super().__init__(self.message)


class EmailAlreadyRegisteredError(DomainError):
    message = "Inscription impossible avec cette adresse"


class InvalidCredentialsError(DomainError):
    message = "Identifiants incorrects"


class InvalidTokenError(DomainError):
    message = "Jeton invalide ou expiré"


class VaultEntryNotFoundError(DomainError):
    message = "Entrée introuvable"
