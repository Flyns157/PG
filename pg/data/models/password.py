# pg.data.models.password.py
"""
Modèles de données pour les mots de passe
"""

from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic import EmailStr
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship

from ...utils.debugging import AutoStrRepr


class PasswordBase(SQLModel, AutoStrRepr):
    user_id: int = Field(foreign_key="user.id", description="Identifiant de l'utilisateur")
    url: str = Field(regex=r'^https?://(?:www\.)?\w+\.\w+$', description="URL du site / service")
    description: str | None = Field(description="Description par l'utilisateur du site / service")
    key: str = Field(description="Clé / identifiant")
    password_encrypted: str = Field(description="Mot de passe chiffré")
    email: EmailStr | None = Field(description="Email associé")
    phone: PhoneNumber | None = Field(description="Numéro de téléphone associé")

class Password(PasswordBase, table=True):
    id: int = Field(default=None, primary_key=True , description="Identifiant de l'enregistrement d'informations de connection")
    date_added: datetime = Field(default_factory=datetime.now, description="Date de création du mot de passe")
    date_updated: datetime = Field(default_factory=datetime.now, description="Date de dernière modification du mot de passe")

    # Relationship to the User model, setting up a one-to-many relationship
    user: "User" = Relationship(back_populates="passwords")
    
    def __str__(self):
        from ...utils.security import decrypt_password
        from ..database import engine
        from .import User

        from sqlmodel import Session, select
        with Session(engine) as session:
            statement = select(User).where(User.id == self.user_id)
            user = session.exec(statement).first()

        return f"\n" \
                f"Site web: {self.url} (id: {self.id})\n" \
                f"Description: {self.description or 'Non spécifié'}\n" \
                f"Identifiant: {self.key}\n" \
                f"Mot de passe: {decrypt_password(self.password_encrypted, user.encryption_key)}\n" \
                f"Email: {self.email or 'Non spécifié'}\n" \
                f"Téléphone: {self.phone or 'Non spécifié'}\n" \
                f"Date de création: {self.date_added}\n" \
                f"Date de dernière modification: {self.date_updated}"

class PasswordCreate(PasswordBase):
    ...

class PasswordUpdate(SQLModel, AutoStrRepr):
    """Modèle pour la mise à jour d'un mot de passe (sans `site`)"""
    description: str | None = None
    key: str | None = None
    password_encrypted: str | None = None
    email: EmailStr | None = None
    phone: PhoneNumber | None = None
