# Interface TUI - Gestionnaire de Mots de Passe

Ce document décrit l'interface utilisateur textuelle (TUI) moderne du gestionnaire de mots de passe, utilisant les bibliothèques **Rich** et **Textual**.

## Prérequis

Assurez-vous d'avoir installé les dépendances :

```bash
pip install -r requirements.txt
```

## Lancement de l'interface TUI

### Méthode 1 : Via la ligne de commande

```bash
python -m pg --mode tui
```

Ou directement :

```bash
python main.py
```

### Méthode 2 : Via Python

```python
from pg import run_app, Mode
run_app(Mode.TUI)
```

## Fonctionnalités

### Écran de connexion
- Saisie du nom d'utilisateur
- Saisie du mot de passe (masqué)
- Boutons Connexion et Inscription
- Validation des champs

### Écran d'inscription
- Création d'un nouveau compte
- Confirmation du mot de passe
- Validation de la force du mot de passe

### Tableau de bord principal
- Affichage des mots de passe dans un tableau interactif
- Barre de recherche en temps réel
- Tri et navigation au clavier
- Indicateur du nombre de mots de passe

### Gestion des mots de passe
- **F1** : Ajouter un nouveau mot de passe
- **F2** : Modifier le mot de passe sélectionné
- **F3** : Supprimer le mot de passe sélectionné
- **F4** : Copier le mot de passe dans le presse-papier
- **F5** : Afficher/Masquer les mots de passe

### Autres commandes
- **Ctrl+Q** : Déconnexion
- **Ctrl+C** : Quitter l'application

## Raccourcis clavier

| Touche | Action |
|--------|--------|
| F1 | Ajouter un mot de passe |
| F2 | Modifier un mot de passe |
| F3 | Supprimer un mot de passe |
| F4 | Copier le mot de passe |
| F5 | Afficher/Masquer les mots de passe |
| Ctrl+Q | Déconnexion |
| Ctrl+C | Quitter |

## Navigation dans les tableaux

- **Flèches** : Se déplacer entre les lignes
- **Entrée** : Valider ou copier
- **Tabulation** : Passer d'un champ à l'autre

## Personnalisation

### Fichier de styles

Le fichier `pg/tui/styles.tcss` contient tous les styles CSS de l'interface. Vous pouvez le modifier pour :

- Changer les couleurs
- Modifier les bordures
- Ajuster les marges et paddings
- Personnaliser les thèmes

### Couleurs disponibles

L'interface utilise les couleurs suivantes :
- **Fond** : `#0f0f1a` (sombre)
- **Accent** : `#3b82f6` (bleu)
- **Erreur** : `#ef4444` (rouge)
- **Succès** : `#10b981` (vert)
- **Avertissement** : `#f59e0b` (orange)
- **Texte** : `#e0e0e0` (gris clair)

## Dépannage

### L'application ne se lance pas

Vérifiez que toutes les dépendances sont installées :
```bash
pip install rich textual
```

### Problèmes d'affichage

L'application nécessite un terminal compatible avec :
- 256 couleurs minimum
- Support UTF-8

### Connexion à la base de données

Assurez-vous que la base de données SQLite existe ou sera créée automatiquement au premier lancement.

## Architecture

```
pg/
├── tui/
│   ├── app.py           # Application principale et écrans
│   ├── styles.tcss      # Styles CSS pour l'interface
│   └── __init__.py      # Initialisation du module
├── data/
│   ├── database.py      # Connexion à la base de données
│   └── models/          # Modèles SQLModel
├── services/            # Logique métier
└── ...
```

## License

Ce projet est sous licence MIT.
