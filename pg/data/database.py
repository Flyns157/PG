import sqlalchemy
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import text
from urllib.parse import urlparse
import datetime

def create_database(connection_string="sqlite:///password_manager.db"):
    """
    Crée une base de données pour le gestionnaire de mots de passe avec les tables nécessaires.
    
    Args:
        connection_string (str): Chaîne de connexion au format SQLAlchemy.
            Exemples:
            - SQLite: "sqlite:///password_manager.db"
            - PostgreSQL: "postgresql://username:password@localhost/dbname"
            - MySQL: "mysql://username:password@localhost/dbname"
            - Oracle: "oracle://username:password@localhost:1521/dbname"
            - SQL Server: "mssql+pyodbc://username:password@server/dbname?driver=ODBC+Driver+17+for+SQL+Server"
    
    Returns:
        sqlalchemy.engine.Engine: Moteur de base de données créé
    """
    # Création du moteur SQLAlchemy
    engine = create_engine(connection_string)
    
    # Création des métadonnées
    metadata = MetaData()
    
    # Définition de la table users
    users = Table('users', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('username', String(100), unique=True, nullable=False),
        Column('password_hash', Text, nullable=False),
        Column('hash_algorithm', String(50), nullable=False),
        Column('encryption_key', Text, nullable=False)
    )
    
    # Définition de la table passwords
    passwords = Table('passwords', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('user_id', Integer, ForeignKey('users.id')),
        Column('site', String(255), nullable=False),
        Column('key', String(255), nullable=False),
        Column('password', Text, nullable=False),
        Column('email', String(255)),
        Column('phone', String(50)),
        Column('date_added', DateTime, default=datetime.datetime),
        Column('date_updated', DateTime, default=datetime.datetime, onupdate=datetime.datetime)
    )
    
    # Création des tables si elles n'existent pas
    metadata.create_all(engine)
    
    return engine