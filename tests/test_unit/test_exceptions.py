"""
Tests unitaires pour les exceptions personalisees.
Teste les classes d'exceptions et leurs comportements.
"""
import pytest

from app.core.exceptions import (
    HTTPExceptionWithDetail,
    CredentialsException,
    NotFoundException,
    ForbiddenException,
    ConflictException,
)


class TestHTTPExceptionWithDetail:
    """Tests pour la classe de base HTTPExceptionWithDetail."""

    def test_exception_with_detail(self):
        """Verifie la creation d'une exception avec detail."""
        exc = HTTPExceptionWithDetail(status_code=400, detail="Bad request")
        assert exc.status_code == 400
        assert exc.detail == "Bad request"

    def test_exception_with_headers(self):
        """Verifie la creation d'une exception avec headers."""
        exc = HTTPExceptionWithDetail(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"}
        )
        assert exc.status_code == 401
        assert exc.detail == "Unauthorized"
        assert exc.headers == {"WWW-Authenticate": "Bearer"}

    def test_exception_inherits_from_httpexception(self):
        """Verifie l'heritage de HTTPException."""
        exc = HTTPExceptionWithDetail(status_code=400, detail="Error")
        assert hasattr(exc, "status_code")
        assert hasattr(exc, "detail")

    def test_exception_attributes_are_accessible(self):
        """Verifie que les attributs sont accessibles."""
        exc = HTTPExceptionWithDetail(status_code=404, detail="Not found")
        assert exc.status_code == 404
        assert exc.detail == "Not found"


class TestCredentialsException:
    """Tests pour CredentialsException."""

    def test_default_message(self):
        """Verifie le message par defaut."""
        exc = CredentialsException()
        assert exc.status_code == 401
        assert "identifiants" in exc.detail.lower()

    def test_custom_message(self):
        """Verifie un message personnalise."""
        exc = CredentialsException(detail="Token invalide")
        assert exc.status_code == 401
        assert exc.detail == "Token invalide"

    def test_exception_type(self):
        """Verifie le type de l'exception."""
        exc = CredentialsException()
        assert isinstance(exc, HTTPExceptionWithDetail)


class TestNotFoundException:
    """Tests pour NotFoundException."""

    def test_default_message(self):
        """Verifie le message par defaut."""
        exc = NotFoundException()
        assert exc.status_code == 404
        assert "non trouvée" in exc.detail.lower() or "trouvée" in exc.detail.lower()

    def test_custom_message(self):
        """Verifie un message personnalise."""
        exc = NotFoundException(detail="Utilisateur non trouvé")
        assert exc.status_code == 404
        assert exc.detail == "Utilisateur non trouvé"


class TestForbiddenException:
    """Tests pour ForbiddenException."""

    def test_default_message(self):
        """Verifie le message par defaut."""
        exc = ForbiddenException()
        assert exc.status_code == 403
        assert "accès" in exc.detail.lower()

    def test_custom_message(self):
        """Verifie un message personnalise."""
        exc = ForbiddenException(detail="Vous n'avez pas le droit")
        assert exc.status_code == 403
        assert exc.detail == "Vous n'avez pas le droit"


class TestConflictException:
    """Tests pour ConflictException."""

    def test_default_message(self):
        """Verifie le message par defaut."""
        exc = ConflictException()
        assert exc.status_code == 409
        assert "conflit" in exc.detail.lower()

    def test_custom_message(self):
        """Verifie un message personnalise."""
        exc = ConflictException(detail="Email déjà utilisé")
        assert exc.status_code == 409
        assert exc.detail == "Email déjà utilisé"

    def test_conflict_for_duplicate_email(self):
        """Test typique: email deja utilise."""
        exc = ConflictException(detail="Un utilisateur avec cet email existe déjà")
        assert exc.status_code == 409


class TestExceptionHierarchy:
    """Tests pour la hierarchie des exceptions."""

    def test_all_exceptions_inherit_from_base(self):
        """Verifie que toutes les exceptions heritent de HTTPExceptionWithDetail."""
        exceptions = [
            CredentialsException(),
            NotFoundException(),
            ForbiddenException(),
            ConflictException(),
        ]
        
        for exc in exceptions:
            assert isinstance(exc, HTTPExceptionWithDetail)

    def test_all_exceptions_are_httpexceptions(self):
        """Verifie que toutes sont des HTTPException."""
        from fastapi import HTTPException
        
        exceptions = [
            HTTPExceptionWithDetail(status_code=400, detail="Error"),
            CredentialsException(),
            NotFoundException(),
            ForbiddenException(),
            ConflictException(),
        ]
        
        for exc in exceptions:
            assert isinstance(exc, HTTPException)

    def test_status_codes_are_correct(self):
        """Verifie les codes de statut corrects."""
        assert HTTPExceptionWithDetail(status_code=400, detail="").status_code == 400
        assert CredentialsException().status_code == 401
        assert ForbiddenException().status_code == 403
        assert NotFoundException().status_code == 404
        assert ConflictException().status_code == 409
