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
| 13 | DAG complet, deux jobs/schedules, stockage durable et file | Jobs multiprocess training/monitoring réussis dans Compose ; schedules et stockage PostgreSQL avec psycopg2 explicite pour les NOTIFY. | terminé |
| 14 | Tests Spark, gate et API ; lint et format | 38 tests réussis avec PostgreSQL réel, dont les 24 exemples du sujet ; Ruff et format réussis. | terminé |
| 15 | Scraping, cinq alertes, dashboard et lecteur SQL | Cible Prometheus UP, cinq alertes chargées ; six panneaux Grafana et deux sources opérationnelles, lecteur SQL sans écriture ; alerte réelle firing. | terminé |
| 16 | Deux images verrouillées, non-root, API sans Java/Spark | Deux builds réels, base Python fixée par digest, caches hors couches, UID 1000 ; API sans Spark/Java et scan bloquant à zéro HIGH/CRITICAL corrigeable. | terminé |
| 17 | Stack complète, utilisateurs séparés, santé, ports locaux, volumes | Une définition Compose, sept services opérationnels ; postgres/mlflow/api healthy. Arrêt complet puis redémarrage sans perte de données ni de champion. | terminé |
| 18 | Smoke authentifié, replay et Locust sur données réelles | Smoke authentifié et replay 200 réussis ; Locust 20 utilisateurs/2 minutes, zéro erreur et p95 25 ms. | terminé |
| 19 | Premier entraînement, promotion, smoke, monitoring et dashboard | Parcours Compose réel réussi : training_job, v1 challenger, promotion, redémarrage, smoke, replay et monitoring_job ; Grafana/Prometheus validés. | terminé |
| 20 | Prix décalés, gate rejetée, rollback, panne DB, mauvaises données | Les cinq exercices ont été exécutés : prix ×1,6, alpha=1000, promotion/rollback, panne DB avec alerte firing et reprise, validation bloquante après corruption. | terminé |
| 21 | CI checks/audit/images/scans, release GHCR et Dependabot | Workflows complétés, PostgreSQL CI isolé, audit Python : aucune vulnérabilité connue. Exécution GitHub et publication d'une release non vérifiées. | partiel |
| 22 | SLO, release/rollback, alertes, rotation et sauvegarde/restauration | Runbook et politique de retraining ; dump restauré dans une base distincte (8 117 prédictions), neuf fichiers MLflow restaurés avec SHA identiques. | terminé |

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

## Preuves de bout en bout

- `docs/TP_EVIDENCE.json` conserve les résultats structurés sans secrets ni données brutes.
- 38 tests réussis avec PostgreSQL réel et deux tests de jointure Feast réelle ; zéro skip
  lors du passage de validation avec TEST_DATABASE_URL.
- Le modèle Compose v1 a un R² holdout de 0,84506, un RMSE de 31 823,15, un MAE
  de 21 833,71 et un MAPE de 0,13406. Split : 1 110 ventes avant juillet 2009
  pour entraîner, 350 ventes à partir de juillet 2009 pour tester.
- Le SHA des fichiers Python du champion a été comparé au code committé : identique.
- Les exercices de sécurité natifs utilisent un registre MLflow SQLite distinct : v3
  de référence, v4 refusée, v5 promue puis rollback. Le registre PostgreSQL Compose
  a été initialisé séparément et sert v1 : ces numéros ne désignent pas le même registre.
- Après redémarrage complet sans `-v`, les sept services fonctionnent, le champion reste
  v1, et le smoke authentifié ainsi que les contrôles d'observabilité repassent.
- Le lecteur Grafana peut lire monitoring_results mais reçoit InsufficientPrivilege en
  tentative d'insertion. Les cinq règles Prometheus sont chargées et la cible est UP.
- La panne PostgreSQL a réellement déclenché PredictionLogFailures en état firing,
  tandis que /predict répondait 200 ; l'ajout de feedback a re-fonctionné après reprise.
- Locust a exécuté environ 7 500 requêtes sur deux minutes à 20 utilisateurs, sans erreur,
  p95 25 ms et p99 45 ms. Le CSV est un instantané périodique (7 508 lignes comptées) ;
  le résumé terminal final compte 7 512 requêtes. Les percentiles concordent.
- Sauvegarde/restauration PostgreSQL : 8 117 prédictions dans la source et la copie,
  dump de 424 411 octets à cet instant. Artefacts MLflow : neuf fichiers restaurés,
  comparaison de tous les SHA-256 sans différence.

## Pull Request

La branche `feat/complete-supinfo-22-steps` est poussée sur `karl9722/modern-mlops-2`.
La création du brouillon via `gh pr create` a échoué sur
`POST https://api.github.com/graphql` avec Forbidden. Il ne s'agit pas d'une PR créée.
La description prête à réutiliser est dans `docs/PR_DESCRIPTION.md` ; ouverture manuelle :
https://github.com/karl9722/modern-mlops-2/pull/new/feat/complete-supinfo-22-steps

## Résultat des contrôles de sécurité

L'audit Python ne signale aucune vulnérabilité connue dans les versions verrouillées.
Le scan bloquant de l'image API est réussi : zéro vulnérabilité HIGH/CRITICAL corrigeable.
Deux composants de build inutiles de la base (setuptools et ses dépendances vendoriées)
ont été désinstallés du runtime, puis l'image a été reconstruite et rescannée.

Le scan complet du pipeline, y compris Java, a terminé après mise en cache de sa base
et augmentation du délai à 15 minutes. Il signale **81 occurrences corrigeables :
77 HIGH et 4 CRITICAL, pour 59 identifiants CVE distincts**, dans les JAR de Spark.
Le sujet impose un scan informatif pour cette image : son exit code 0 ne signifie
pas absence de vulnérabilités. Les quatre critiques concernent Netty, Avro, Derby et
ZooKeeper ; les versions et correctifs sont conservés dans TP_EVIDENCE.json.
Ces alertes ne sont ni masquées ni ignorées par une exception CVE ; elles restent
une limite de sécurité à traiter avant tout usage en production.

La PR n'est pas créée : la branche et sa description sont prêtes, mais l'API GraphQL
GitHub refuse la requête. Le brouillon réseau doit être activé dans les paramètres
pour autoriser api.github.com ; un nouvel essai restera nécessaire pour vérifier
l'autorisation API et l'exécution de la CI.
