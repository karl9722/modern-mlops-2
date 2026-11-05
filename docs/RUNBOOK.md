# RUNBOOK — Modern MLOps

## 1. Services

| Service | Adresse |
|---|---|
| FastAPI | http://localhost:8001 |
| MLflow | http://localhost:5000 |
| Dagster | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

## 2. Démarrage

Démarrer les services principaux :

`docker compose -f docker-compose.yml -f docker-compose.app.yml up -d`

Démarrer le monitoring :

`docker compose -f docker-compose.monitoring.yml -f docker-compose.grafana.yml up -d`

## 3. Tests

Exécuter les commandes suivantes :

- `uv run ruff check src tests`
- `uv run pytest -q`
- `uv run python scripts/smoke_test.py`

Les trois commandes doivent réussir.

## 4. Monitoring

Dans Grafana, ouvrir le dashboard **Modern MLOps - API Monitoring**.

Surveiller les requêtes HTTP, les erreurs 5xx et la latence p95.

Dans Prometheus, vérifier que `up{job="fastapi"}` vaut `1`.

## 5. Gestion des incidents

Si l'API est indisponible, vérifier les conteneurs et leurs logs.

Si le modèle ne se charge pas, vérifier MLflow et les logs FastAPI.

Si la latence augmente, consulter Grafana et vérifier les ressources avec `docker stats`.

## 6. Déploiement et rollback

Avant un déploiement, exécuter les tests, vérifier le modèle dans MLflow et lancer le smoke test.

En cas d'échec, restaurer la version précédente du modèle et redémarrer l'API.

La procédure de rollback doit encore être testée.

## 7. Sécurité

- Ne pas publier le fichier `.env`.
- Ne pas stocker les secrets dans Git.
- Limiter les ports exposés.
- Vérifier l'authentification avant une mise en production.

## 8. Objectifs SLO

- Disponibilité cible : 99 %.
- Latence p95 cible : inférieure à 200 ms.
- Surveiller les erreurs HTTP 5xx et la dérive du modèle.

Ces valeurs sont des objectifs à mesurer, et non des performances déjà garanties.