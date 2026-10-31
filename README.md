# PG

(Password Gestion) Gestionnaire de mots de passe local et multi-utilisateur : un seul exécutable, un coffre SQLite chiffré, une interface en terminal (TUI), une interface graphique (GUI), ou les deux.

Cette V3 en Rust remplace à terme l'application Python du dossier `pg/`.

## Compilation

Il faut [Rust](https://rustup.rs) stable (testé avec la 1.99) et un compilateur C, car SQLite est embarqué dans l'exécutable.

| Variante | Commande | Taille sous Windows |
| --- | --- | --- |
| TUI et GUI | `cargo build --release` | 6,8 Mo |
| TUI seule | `cargo build --release --no-default-features --features tui` | 2,9 Mo |
| GUI seule | `cargo build --release --no-default-features --features gui` | 6,6 Mo |

L'exécutable se trouve dans `target/release/`. Sous Windows, il ne dépend d'aucune DLL Visual C++. Sous Linux, la GUI a besoin des bibliothèques système de X11 ou Wayland.

## Apparence

La GUI reprend le style de Windows 11 et suit le mode clair ou sombre du système. Sous Windows, elle utilise les polices Segoe UI et Segoe Fluent Icons déjà installées ; ailleurs, elle garde sa police intégrée et ses boutons restent sans icône. La TUI suit les couleurs du terminal.

## Raccourcis de la GUI

| Touche | Action |
|---|---|
| Ctrl+F | Aller à la recherche |
| ↑ / ↓ | Parcourir la liste |
| Ctrl+C | Copier le mot de passe de l'entrée sélectionnée |
| Ctrl+B | Copier l'identifiant |
| Ctrl+N | Ajouter une entrée |
| Suppr | Supprimer l'entrée, après confirmation |
| Entrée | Valider le formulaire |
| Échap | Fermer le formulaire |

## Utilisation

```
pg [--interface tui|gui] [--db FICHIER]
```

- Sans `--interface`, PG lance la GUI si elle est compilée, sinon la TUI.
- Sans `--db` ni variable `PG_DB`, la base est créée dans le dossier de données de l'utilisateur (`%APPDATA%\PG\data\pg.db` sous Windows, `~/.local/share/pg/pg.db` sous Linux).

Touches de la TUI : `/` chercher, `v` afficher le mot de passe, `c` le copier, `u` copier l'identifiant, `a` ajouter, `e` modifier, `d` supprimer, `i` importer, `x` exporter, `m` changer le mot de passe maître, `l` verrouiller, `q` quitter. Dans un formulaire d'entrée, `Ctrl+G` génère un mot de passe et `Ctrl+R` affiche le champ.

## Sécurité

- **Mot de passe maître :** il n'est jamais stocké. Argon2id (64 Mio, 3 passes) en dérive une clé qui protège une clé de coffre aléatoire.
- **Entrées :** chacune est chiffrée entièrement avec XChaCha20-Poly1305, site et identifiant compris. La base ne révèle que les noms d'utilisateur et le nombre d'entrées de chacun.
- **Session :** le coffre se verrouille après 5 minutes d'inactivité. Le presse-papiers est effacé après 30 secondes s'il contient encore le secret copié. Sous Windows, les copies sont exclues de l'historique et de la synchronisation.

Limites à connaître :

- Un mot de passe maître oublié rend le coffre irrécupérable.
- Les exports CSV sont en clair. PG n'écrase jamais un fichier existant.
- L'effacement des secrets en mémoire est au mieux : l'interface graphique et les bibliothèques peuvent en garder des copies temporaires.
- Ce logiciel n'a pas fait l'objet d'un audit de sécurité externe.

## Reprendre un coffre de la version Python

Les deux formats de base sont incompatibles : la migration passe par le CSV.

1. Dans l'ancienne application, exportez vos mots de passe en CSV.
2. Dans PG V3, créez un compte, puis importez ce fichier. Les colonnes sont reconnues quel que soit leur ordre et les doublons sont ignorés.
3. Supprimez le fichier CSV, ainsi que l'ancien `password_manager.db` et ses sauvegardes.

## Importer depuis un navigateur

PG importe aussi les exports CSV de mots de passe de Chromium (`name,url,username,password,note`). Toutes les lignes doivent avoir un identifiant et un mot de passe : sinon, l'import s'arrête en indiquant la ligne à corriger.

## Serveur MCP intégré

PG peut exposer le coffre à un client IA via MCP. Le serveur est désactivé à chaque lancement. Pour l'activer ou le désactiver, une fois le coffre déverrouillé, utilisez le bouton **Accès pour assistants IA** en GUI ou la touche `p` en TUI. Il écoute sur `http://127.0.0.1:39517/mcp`.

Chaque activation crée un nouveau jeton et le copie dans le presse-papiers (bouton **Copier le jeton d'accès** ou touche `P` pour le recopier). Le client doit donc être reconfiguré à chaque activation :

```
claude mcp add --transport http pg http://127.0.0.1:39517/mcp --header "Authorization: Bearer <jeton>"
```

| Outil | Effet |
|---|---|
| `search_entries` | Renvoie l'id, le site, l'identifiant et les notes des entrées |
| `copy_password` | Copie un mot de passe dans le presse-papiers, effacé après 30 secondes, et l'indique dans PG |

Limites à connaître :

- Les mots de passe ne sont jamais renvoyés au client. Les sites, identifiants et **notes** le sont, et peuvent donc partir vers le fournisseur d'IA : ne gardez pas de secret dans les notes si vous activez le MCP.
- `copy_password` ne demande pas de confirmation. Tout programme qui lit le presse-papiers peut lire le mot de passe copié.
- Les appels MCP ne repoussent pas le verrouillage automatique. Le verrouillage arrête le serveur : réactivez-le ensuite, ce qui crée un nouveau jeton.

## Développement

```
cargo test
cargo clippy --all-targets
```
