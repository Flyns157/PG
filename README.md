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
- **Session :** le coffre se verrouille après 5 minutes d'inactivité. Le presse-papiers est effacé après 30 secondes s'il contient encore le secret copié.

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

## Développement

```
cargo test
cargo clippy --all-targets
```
