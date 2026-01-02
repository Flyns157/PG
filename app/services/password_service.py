"""
Service métier pour la gestion des mots de passe.

Ce module contient toute la logique métier liée à la gestion
des entrées de mots de passe : CRUD et recherche.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.password import PasswordEntry
from app.schemas.password import PasswordCreate, PasswordUpdate


class PasswordService:
    """
    Service de gestion des mots de passe.

    Gère toutes les opérations CRUD sur les entrées de mots de passe
    avec vérification des droits d'accès.
    """

    def __init__(self, db: Session, user_id: int):
        """
        Initialise le service avec une session et un ID d'utilisateur.

        Args:
            db: Session SQLAlchemy pour les opérations de base de données.
            user_id: ID de l'utilisateur propriétaire des entrées.
        """
        self.db = db
        self.user_id = user_id

    def create(self, password_data: PasswordCreate) -> PasswordEntry:
        """
        Crée une nouvelle entrée de mot de passe.

        Args:
            password_data: Données de l'entrée à créer.

        Returns:
            L'entrée de mot de passe créée.
        """
        entry = PasswordEntry(
            user_id=self.user_id,
            service_name=password_data.service_name,
            username=password_data.username,
            password_value=password_data.password_value,
            notes=password_data.notes,
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        return entry

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> tuple[List[PasswordEntry], int]:
        """
        Récupère toutes les entrées de mots de passe de l'utilisateur.

        Args:
            skip: Nombre d'entrées à sauter (pagination).
            limit: Nombre maximum d'entrées à retourner.
            search: Terme de recherche optionnel sur le nom du service ou username.

        Returns:
            Tuple contenant la liste des entrées et le total.
        """
        query = self.db.query(PasswordEntry).filter(
            PasswordEntry.user_id == self.user_id
        )

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (PasswordEntry.service_name.ilike(search_term)) |
                (PasswordEntry.username.ilike(search_term))
            )

        total = query.count()
        entries = query.order_by(PasswordEntry.created_at.desc()) \
            .offset(skip).limit(limit).all()

        return entries, total

    def get_by_id(self, entry_id: int) -> PasswordEntry:
        """
        Récupère une entrée de mot de passe par son ID.

        Args:
            entry_id: ID de l'entrée à récupérer.

        Returns:
            L'entrée de mot de passe trouvée.

        Raises:
            NotFoundException: Si l'entrée n'existe pas.
            ForbiddenException: Si l'entrée n'appartient pas à l'utilisateur.
        """
        entry = self.db.query(PasswordEntry).filter(
            PasswordEntry.id == entry_id
        ).first()

        if not entry:
            raise NotFoundException(
                detail="Entrée de mot de passe non trouvée")

        if entry.user_id != self.user_id:
            raise ForbiddenException(
                detail="Vous n'avez pas accès à cette entrée de mot de passe"
            )

        return entry

    def update(
        self,
        entry_id: int,
        update_data: PasswordUpdate
    ) -> PasswordEntry:
        """
        Met à jour une entrée de mot de passe.

        Args:
            entry_id: ID de l'entrée à mettre à jour.
            update_data: Données de mise à jour (partielles ou complètes).

        Returns:
            L'entrée de mot de passe mise à jour.
        """
        entry = self.get_by_id(entry_id)

        # Mise à jour des champs non-None
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(entry, field, value)

        self.db.commit()
        self.db.refresh(entry)

        return entry

    def delete(self, entry_id: int) -> bool:
        """
        Supprime une entrée de mot de passe.

        Args:
            entry_id: ID de l'entrée à supprimer.

        Returns:
            True si la suppression a réussi.
        """
        entry = self.get_by_id(entry_id)

        self.db.delete(entry)
        self.db.commit()

        return True

    def get_by_service(self, service_name: str) -> List[PasswordEntry]:
        """
        Récupère toutes les entrées pour un service spécifique.

        Args:
            service_name: Nom du service à rechercher.

        Returns:
            Liste des entrées pour ce service.
        """
        return self.db.query(PasswordEntry).filter(
            PasswordEntry.user_id == self.user_id,
            PasswordEntry.service_name.ilike(service_name)
        ).all()
