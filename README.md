# TP SUPINFO 5LAKE — modern-mlops-2

Pipeline Ames : validation PySpark → jointure temporelle Feast → Ridge/log-prix →
MLflow et gate → promotion manuelle → API authentifiée → PostgreSQL → monitoring.
Ce dépôt est indépendant de `modern-mlops` : projet Compose, images et volumes portent
le préfixe `modern-mlops-2`.

L'implémentation reprend les exemples du sujet fourni
« SUPINFO - 5LAKE: Build a Production MLOps Pipeline with OSS », adaptés aux versions
verrouillées existantes (MLflow 3, Feast 0.67, NumPy 2). Voir
[l'audit des 22 étapes](docs/TP_AUDIT.md) pour les écarts initiaux et les preuves obtenues.

## Installer et tester

Prérequis : Git, Python 3.11, uv 0.13.4, Java 17, Docker Engine et Compose v2.
Prévoir au moins 6 Go de RAM et suffisamment de disque pour les images.

```bash
uv sync --frozen --all-groups
uv run python scripts/init_env.py
uv run --frozen --all-groups ruff check .
uv run --frozen --all-groups ruff format --check .
uv run --frozen --all-groups pytest -q
docker compose config --quiet
docker compose up --build -d
```

`.env` reste local. Aucun mot de passe de l'exemple ne doit être utilisé en service.
Les tests unitaires ne dépendent pas de MLflow ; le test PostgreSQL s'exécute avec
`TEST_DATABASE_URL` pointant vers une base de test isolée. La CI en démarre une.
Les images installent séparément les dépendances API, pipeline et développement.
Le cache de téléchargement uv est un montage BuildKit, jamais une couche d'image.

## Premier modèle

Dans Dagster, lancer `training_job`, ou :

```bash
docker compose exec dagster-daemon dagster job execute -m mlops.orchestration -j training_job
docker compose exec api mlops-model status
docker compose exec api mlops-model promote
docker compose restart api
uv run --all-groups --env-file .env python scripts/smoke_test.py
```

Le premier `/ready` répond 503 tant qu'aucun champion n'est promu. Passer la gate
attribue seulement `challenger`, jamais `champion`. L'API charge une version explicite
au démarrage et la conserve jusqu'au redémarrage.

| Service | Port local |
|---|---|
| API et documentation OpenAPI | 8001 |
| MLflow | 5000 |
| Dagster | 3000 |
| Prometheus | 9090 |
| Grafana | 3001 |
| PostgreSQL | 5435 (configurable) |

Tous les ports sont liés à `127.0.0.1`. L'autorisation OpenAPI utilise `X-API-Key`.

## Monitoring et exercices

```bash
uv run --all-groups --env-file .env python scripts/replay_holdout.py --rows 200
docker compose exec dagster-daemon dagster job execute -m mlops.orchestration -j monitoring_job
```

`training_job` est planifié le lundi à 06:00 UTC ; `monitoring_job` tous les jours
à 07:00 UTC. Les observations insuffisantes sont enregistrées comme *skipped*
(`passed = NULL`) et ne constituent pas une réussite.

`scripts/verify_tp.py` exerce les jobs réels, la gate, la promotion/rollback, les prix
décalés et les données corrompues. Il modifie volontairement le registre local et
doit être lancé uniquement sur une stack de développement isolée. Il conserve ses
preuves dans `artifacts/reports/verification.json` et restaure le CSV original.

Pour un environnement empêchant OpenML, `RAW_DATA_URL` peut sélectionner un miroir
HTTPS explicite ; `RAW_DATA_SHA256` est alors obligatoire. La source et le hash sont
conservés avec les rapports et la fiche modèle. Aucun repli silencieux sur des données
synthétiques n'est effectué. Voir l'audit pour le miroir exact utilisé lors des tests.

Les conteneurs démarrés dans un cloud avec proxy TLS nécessitent le certificat
de confiance de cette plateforme : les Dockerfiles acceptent le secret BuildKit
`proxy_ca`. La vérification TLS reste active.

Consulter le [runbook](docs/RUNBOOK.md) pour les alertes, sauvegardes, restauration,
rotation des clés et procédures de release. `docker compose down` conserve les données ;
ne pas ajouter `-v` sauf suppression volontaire.
