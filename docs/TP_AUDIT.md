# Audit du TP SUPINFO 5LAKE — 22 étapes

Périmètre : uniquement `karl9722/modern-mlops-2`, à partir du commit
`15df8d4c40a301ae8b9f087748ee572885f0ad2a`. Le dépôt original `modern-mlops`
n'a été ni modifié, ni utilisé pour les conteneurs, volumes ou publications.

Référence : pièce jointe `SUPINFO---5LAKE-Build-a-Production-MLOps-Pipeline-with-OSS.md`.
Les exemples du sujet ont été comparés aux fichiers existants et adaptés, sans remplacer
les versions fonctionnelles par les anciennes bornes du document. Les états ci-dessous
décrivent les preuves obtenues, pas seulement la présence de fichiers.

| Étape | Exigence et écart initial | Réalisation et vérification | Statut |
|---|---|---|---|
| 1 | Git, Python 3.11, uv, Java 17, Docker/Compose | Outils CLI disponibles ; les extensions d'un IDE local ne sont pas vérifiables depuis ce cloud. | partiel |
| 2 | Structure, secrets ignorés, attributs LF, contexte Docker | Structure complétée, `.env` ignoré, générateur de secrets sans écrasement, sauvegardes exclues de Git et Docker. | terminé |
| 3 | Dépendances main/pipeline/dev, lock, CLI registre | Groupes séparés, `uv.lock` actualisé, installation frozen, imports et commande `mlops-model`. | terminé |
| 4 | Configuration centralisée et logs JSON avec request_id | `settings.py`, `logging_config.py`, middleware ; en-tête request_id testé. | terminé |
| 5 | Téléchargement Ames, validation bloquante Spark, Parquet et empreinte | 1 460 lignes réelles préparées ; validation des colonnes, volume, null/NaN, plages, doublons et dates fractionnaires. Accès OpenML direct bloqué ; miroir explicite vérifié utilisé. | partiel |
| 6 | Feast hors ligne et jointure point-in-time sans fuite de cible | Source sans SalePrice ; tests réels Feast : aucune lecture du futur, refus des ventes sans caractéristiques historiques. | terminé |
| 7 | MAE/RMSE/R²/MAPE, comportement, seuil et comparaison au champion | Tests de gate et des valeurs non finies ; alpha=1000 refusé sur le même holdout. | terminé |
| 8 | Split temporel, Ridge/log-prix, traçabilité et fiche modèle MLflow | Entraînement Ames réel, métriques et signature, validation/empreinte, modèle versionné, fiche modèle, alias challenger uniquement. | terminé |
| 9 | CLI status/promote/rollback, refus des modèles rejetés, historique | Promotion et rollback réels avec redémarrages API et vérification de version ; refus d'une version rejetée. | terminé |
| 10 | Prédictions, feedback, checks PostgreSQL, pool et reprise | Test PostgreSQL réel : UUID, JSONB, feedback inconnu/upsert, résultat skipped NULL et nettoyage. | terminé |
| 11 | Champion, health/ready, clés, schémas stricts, métriques, résilience | Tests des cinq endpoints, autorisation OpenAPI, refus 401/422/503, stockage et version de modèle. | terminé |
| 12 | Evidently, RMSE réelle, fenêtres et minimums, skipped explicites | Drift 0 ; RMSE réelle ~32 588 contre limite ~47 735 ; prix ×1,6 : échec ~130 696. HTML Evidently conservé. | terminé |
| 13 | DAG complet, deux jobs/schedules, stockage durable et file | Jobs natifs exécutés ; PostgreSQL utilise explicitement psycopg2 pour les NOTIFY Dagster sous SQLAlchemy 2.1. Validation de la stack en cours. | partiel |
| 14 | Tests Spark, gate et API ; lint et format | 38 tests réussis avec PostgreSQL réel, dont les 24 exemples du sujet ; Ruff et format réussis. | terminé |
| 15 | Scraping, cinq alertes, dashboard et lecteur SQL | Provisioning complété ; endpoints Prometheus/Grafana répondent ; vérification fonctionnelle finale en cours. | partiel |
| 16 | Deux images verrouillées, non-root, API sans Java/Spark | Builds réels ; base Python fixée par digest ; caches hors couches ; correction des composants de build vulnérables du runtime. Scan final en cours. | partiel |
| 17 | Stack complète, utilisateurs séparés, santé, ports locaux, volumes | Une définition Compose remplace les fragments incohérents ; sept services démarrent et répondent. Parcours conteneur en cours. | partiel |
| 18 | Smoke authentifié, replay et Locust sur données réelles | Smoke et 200 prédictions/feedback réels réussis ; test de charge à finaliser. | partiel |
| 19 | Premier entraînement, promotion, smoke, monitoring et dashboard | Parcours natif réussi ; parcours complet dans Compose en cours. | partiel |
| 20 | Prix décalés, gate rejetée, rollback, panne DB, mauvaises données | Quatre exercices natifs réussis ; panne/alerte PostgreSQL à finaliser dans Compose. | partiel |
| 21 | CI checks/audit/images/scans, release GHCR et Dependabot | Workflows complétés, PostgreSQL CI isolé, audit Python : aucune vulnérabilité connue. Exécution GitHub et publication d'une release non vérifiées. | partiel |
| 22 | SLO, release/rollback, alertes, rotation et sauvegarde/restauration | Runbook complété avec procédures sûres ; exercice de restauration à finaliser. | partiel |

## Choix techniques et écarts justifiés

- Le contrat initial (surface/bedrooms/age/distance_center sur données synthétiques)
  ne répondait pas au sujet Ames : il a été remplacé par OverallQual, GrLivArea,
  GarageCars, TotalBsmtSF et YearBuilt. Les anciens points d'entrée appellent le vrai pipeline.
- Les dépendances existantes MLflow 3.18, Feast 0.67, NumPy 2 et SQLAlchemy 2.1 sont
  conservées. La sérialisation skops autorise seulement `numpy.dtype`, nécessaire à
  Ridge ; les erreurs réseau du registre ne sont pas confondues avec un alias absent.
- Le projet Compose, les images et volumes utilisent `modern-mlops-2`. Les anciennes
  définitions multiples ont été consolidées ; les ports restent locaux (API 8001, DB 5435).
- Les skips monitoring sont persistés comme NULL avec leur raison ; ils ne sont pas
  présentés comme des contrôles réussis.
- Les builds ont été adaptés au pilote Docker vfs de ce cloud : caches uv en montages
  BuildKit et runtime séparé. Aucun contrôle TLS, checksum ou gate n'a été désactivé.

## Données et provenance

OpenML reste la source par défaut. La politique réseau de cette session refuse OpenML.
La validation a donc utilisé le CSV Ames public de ce miroir immuable :

`https://raw.githubusercontent.com/krishnaik06/Advanced-House-Price-Prediction-/92cc6f59c373afd965bdadf3568c597926295c44/train.csv`

SHA-256 : `1e18addf81e5e4d347cc17ee6075bbe4a42b7fa26b9e5b063e8f692a5f929d41`.
Le CSV contient 1 460 ventes et toutes les colonnes requises. Il n'est pas committé.
Pour le sélectionner, définir explicitement `RAW_DATA_URL` et `RAW_DATA_SHA256`.
La source est conservée dans `housing.source.json`, le résumé et la fiche modèle.

## Reproduire les vérifications

```bash
uv sync --frozen --all-groups
uv run python scripts/init_env.py
uv run --frozen --all-groups ruff check .
uv run --frozen --all-groups ruff format --check .
uv run --frozen --all-groups pytest -q
docker compose config --quiet
docker compose up --build -d
```

Le test PostgreSQL exige `TEST_DATABASE_URL` vers une base isolée ; la CI le renseigne.
Sur une stack de développement seulement, `scripts/verify_tp.py` exécute les jobs et
les exercices de modèles/données ; `scripts/verify_operations.py` exerce la panne et
restaure une sauvegarde dans une base temporaire distincte. Les rapports générés
restent sous `artifacts/reports/` (ignoré par Git).

## Limites externes

L'accès Git HTTPS au dépôt fonctionne. L'API GitHub répond actuellement Forbidden,
ce qui empêche la création distante de la PR et l'observation des Actions. Les domaines
OpenML et `api.github.com` ont été ajoutés au brouillon réseau ; ce brouillon n'active
pas lui-même une nouvelle politique. Aucune release ni image GHCR n'a été publiée.
