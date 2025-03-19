# pg.utils.search_engine.py
from fuzzywuzzy import process

from ..data.models import Password

def similar_passwords(liste_objets: Password, cible: str) -> list[Password]:
    """
    Trouve les objets dont l'attribut .url est le plus proche de la chaîne cible.

    :param liste_objets: Liste d'objets avec un attribut .url
    :param cible: La chaîne de référence
    :return: Liste des objets triés par similarité décroissante
    """
    # Créer une liste des URLs à comparer
    urls = [obj.url for obj in liste_objets]

    # Trouver les correspondances avec leurs scores
    correspondances = process.extract(cible, urls, limit=len(urls))

    # Trier les objets en fonction des scores
    objets_triés = sorted(
        liste_objets,
        key=lambda obj: next(score for url, score in correspondances if url == obj.url),
        reverse=True
    )

    return objets_triés