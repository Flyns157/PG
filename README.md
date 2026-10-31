# PG API

API de coffre-fort pour mots de passe, construite avec FastAPI, SQLAlchemy 2 et PostgreSQL.

Le serveur fonctionne à **connaissance nulle** : il ne reçoit ni le mot de passe maître, ni la clé de chiffrement, ni le contenu des entrées. Le nom du service, l'identifiant, le secret et les notes sont tous dans le texte chiffré. La recherche se fait donc côté client.

## Contrat de chiffrement côté client

| Étape | Traitement |
| --- | --- |
| Dérivation | `scrypt(mot de passe maître, sel, n, r, p, dklen=64)` |
| Clé de chiffrement | 32 premiers octets, jamais envoyés |
| Vérificateur | 32 derniers octets en hexadécimal, envoyés comme `auth_verifier` à l'inscription et comme `password` à la connexion |
| Entrée | AES-256-GCM avec un nonce aléatoire de 12 octets par écriture ; texte chiffré (tag inclus) et nonce en base64 |

Coût minimal imposé : `n = 2^15`, `r = 8`, `p = 1`.

**Conséquence :** un mot de passe maître perdu rend le coffre illisible. L'API ne propose donc aucune récupération de compte.

## Parcours

1. **Inscription :** le client génère un sel de 16 octets, dérive ses clés, puis appelle `POST /users/signup`.
2. **Connexion :** le client récupère le sel avec `POST /login/parameters`, dérive ses clés, puis appelle `POST /login/access-token`.
3. **Coffre :** le client chiffre et déchiffre localement, et échange des entrées opaques avec `/vault-entries/`.

## Endpoints

Tous sont préfixés par `/api/v1`. La documentation interactive est disponible sur `/docs`.

| Méthode | Chemin | Description |
| --- | --- | --- |
| POST | `/login/parameters` | Paramètres de dérivation d'un compte |
| POST | `/login/access-token` | Connexion OAuth2, renvoie un JWT |
| POST | `/users/signup` | Inscription |
| GET | `/users/me` | Compte connecté |
| DELETE | `/users/me` | Supprime le compte et son coffre |
| GET, POST | `/vault-entries/` | Liste paginée, création |
| GET, PUT, DELETE | `/vault-entries/{id}` | Lecture, remplacement, suppression |
| GET | `/utils/health-check` | Sonde de disponibilité |

## Développement

Prérequis : [uv](https://docs.astral.sh/uv/) et Docker.

```bash
cp .env.example .env
```

Remplacez ensuite chaque `changethis` dans `.env`, puis lancez la base et l'API :

```bash
docker compose up -d db
```

```bash
cd backend
uv sync
uv run bash scripts/prestart.sh
uv run fastapi dev
```

Pour tout lancer dans Docker :

```bash
docker compose watch
```

## Vérifications

Depuis `backend/` :

```bash
uv run bash scripts/lint.sh
```

```bash
uv run bash scripts/test.sh
```

Les tests utilisent une base SQLite temporaire, ou celle de `TEST_DATABASE_URL` si elle est définie, jamais `DATABASE_URL`. La CI les exécute sur PostgreSQL, avec un seuil de couverture de 90 %. **La base désignée par `TEST_DATABASE_URL` est vidée à chaque test.**

Après une modification des modèles :

```bash
uv run alembic revision --autogenerate -m "description"
```

## Structure

```text
backend/
├── app/
│   ├── main.py      # assemblage de l'application
│   ├── api/         # routes, dépendances, traduction des erreurs en HTTP
│   ├── core/        # configuration, base, sécurité, erreurs métier
│   ├── models/      # tables SQLAlchemy
│   ├── schemas/     # contrats d'entrée et de sortie
│   ├── services/    # logique métier, sans dépendance HTTP
│   └── alembic/     # migrations
├── scripts/
└── tests/
```

## Limites connues

- **Limitation de débit :** les compteurs sont en mémoire et par processus, d'où un seul worker dans l'image. Pour passer à plusieurs instances, il faut un stockage partagé comme Redis.
- **Proxy :** le débit est compté par adresse du client directe. Derrière un proxy, configurez `--forwarded-allow-ips` pour obtenir la vraie adresse.
- **Inscription :** la réponse 409 révèle qu'une adresse est déjà prise, faute de vérification par email.
- **Mot de passe maître :** le changer impose de rechiffrer tout le coffre ; ce parcours n'existe pas encore.
- **Jetons :** il n'y a pas de refresh token, le client se reconnecte à l'expiration.

## Licence

MIT
