# Guide d'utilisation - Interface Textual TUI

## Introduction

L'interface TUI (Text User Interface) Textual offre une expérience utilisateur moderne et interactive directement dans votre terminal. Cette interface remplace l'ancienne interface console basique par un design soigné avec des animations, des couleurs et une navigation intuitive.

## Installation

```bash
# Installer les dépendances
pip install -r requirements.txt

# Ou avec uv
uv pip install -r requirements.txt
```

## Lancement

### Mode TUI (Textual)
```bash
python -m pg --mode tui
```

### Mode GUI (Tkinter - existant)
```bash
python -m pg --mode gui
```

### Mode Console (basique - existant)
```bash
python -m pg --mode console
```

## Fonctionnalités de l'interface TUI

### 1. Écran de connexion
- **Design moderne** : Gradients, bordures arrondies, ombres
- **Validation en temps réel** : Messages d'erreur instantanés
- **Animations fluides** : Transitions lors de l'affichage
- **Raccourcis** : Navigation au clavier

### 2. Écran d'inscription
- **Validation du mot de passe** : Vérification des exigences
- **Indicateurs visuels** : Couleurs pour success/error
- **Messages d'aide** : Requirements affichés

### 3. Tableau de bord principal

#### Sidebar (gauche)
- **Informations utilisateur** : Avatar et nom
- **Barre de recherche** : Filtrage instantané
- **Actions rapides** : Ajouter, Modifier, Supprimer
- **Gestion des données** : Export/Import
- **Déconnexion** : Retour à l'écran de connexion

#### Zone principale (droite)
- **Header** : Titre de l'application avec horloge
- **DataTable** : Liste des mots de passe avec pagination virtuelle
- **Status bar** : Informations sur le nombre d'éléments

### 4. Modales

#### Ajouter/Modifier un mot de passe
- Champs avec icônes et labels clairs
- Validation des champs obligatoires
- Sauvegarde avec feedback visuel

#### Import/Export CSV
- Interface dédiée pour les opérations de fichiers
- Messages de statut clairs
- Support du format CSV standard

#### Confirmation de suppression
- Warning visuel avec icône d'alerte
- Confirmation explicite requise

## Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `A` | Ajouter un mot de passe |
| `E` | Modifier le mot de passe sélectionné |
| `D` | Supprimer le mot de passe sélectionné |
| `R` | Afficher/Masquer les mots de passe |
| `F` / `Ctrl+F` | Focus sur la recherche |
| `F1` | Afficher l'aide |
| `F5` | Rafraîchir la liste |
| `Q` / `Ctrl+Q` | Quitter l'application |
| `L` | Déconnexion |
| `ESC` | Retour / Fermer |
| `↑` / `↓` | Naviguer dans le tableau |
| `Tab` | Navigation entre les champs |

## Thème visuel

L'interface utilise un thème sombre moderne avec :
- **Couleurs primaires** : Violet/bleu (#667eea, #764ba2)
- **Couleurs de fond** : Bleu nuit (#0f0f23, #1a1a2e)
- **Accentuation** : Cyan (#4ecdc4) pour les succès
- **Alertes** : Rouge (#ff6b6b) pour les erreurs

### Éléments stylisés

- **Boutons** : Gradients, effets hover, bordures arrondies
- **Inputs** : Bordures animées, focus glow
- **Tableaux** : Alternance de lignes (zebra stripes), highlight au survol
- **Modales** : Arrières-plans semi-transparents, ombres portées

## Structure du code

```
pg/
├── __init__.py          # Point d'entrée avec Mode.TUI
├── __main__.py          # Argument parsing
├── console.py           # Interface Textual complète
│   ├── MODERN_DARK_CSS  # Styles globaux
│   ├── LoginScreen      # Écran de connexion
│   ├── RegisterScreen   # Écran d'inscription
│   ├── DashboardScreen  # Tableau de bord principal
│   ├── PasswordModal    # Modale CRUD mots de passe
│   ├── ImportExportModal# Modale Import/Export
│   ├── ConfirmModal     # Modale de confirmation
│   ├── HelpScreen       # Écran d'aide
│   └── PasswordManagerApp# Application principale
```

## Intégration avec le code existant

L'interface Textual utilise les mêmes modèles et services que les interfaces existantes :

- **Models** : `User`, `Password` (data/models/)
- **Database** : `engine` (data/database.py)
- **Services** : `similar_passwords`, `export_passwords`, `import_passwords`

## Dépannage

### L'application ne démarre pas
```bash
# Vérifier les dépendances
pip install textual>=6.11.0

# Tester l'import
python -c "from pg.console import PasswordManagerApp"
```

### Problèmes d'affichage
- Vérifier que le terminal supporte les couleurs 24-bit
- Augmenter la taille du terminal (minimum 80x24)
- Éviter les émulateurs de terminal anciens

### Performance lente
- Les opérations de base de données sont exécutées dans des workers
- Si des ralentissements sont constatés, vérifier la taille de la base de données

## Améliorations futures potentielles

- [ ] Support du clipboard pour copier les mots de passe
- [ ] Générateur de mots de passe sécurisé
- [ ] Synchronisation cloud
- [ ] Thèmes personnalisables
- [ ] Mode high-contrast pour l'accessibilité
- [ ] Support mobile/responsive (via Textual web)

## Notes techniques

- **Textual 6.11.0** : Dernière version stable au moment de l'écriture
- **Threading** : Utilisation de `@work(thread=True)` pour les opérations DB
- **Animations** : CSS animations via le système TCSS de Textual
- **Reactive** : Réactivité automatique pour les changements de données

---

Développé avec ❤️ utilisant Textual 6.11.0
