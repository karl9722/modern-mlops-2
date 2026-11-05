## Problème et résultat

Le dépôt ne couvrait qu'une démonstration de prix immobiliers sur données synthétiques.
Cette PR complète les exigences du TP SUPINFO 5LAKE : un modèle Ames est entraîné sur
des données validées, versionné et soumis à une gate, puis servi uniquement après une
promotion explicite. Prédictions et feedback alimentent le monitoring réel.

## Changements

- Contrat Ames, validation Spark bloquante, empreinte des données et jointure historique Feast.
- Ridge avec prétraitement embarqué, split temporel, métriques, fiche modèle, traçabilité
  des sources et comparaison du candidat au champion sur le même holdout.
- CLI status/promote/rollback avec refus des versions rejetées et historique de promotion.
- API avec X-API-Key, readiness, schémas stricts, UUID/version, logs JSON et métriques ;
  persistance PostgreSQL, feedback, reprise après panne et lecteur Grafana limité en lecture.
- Checks Evidently/RMSE, vrais résultats skipped, jobs/schedules Dagster et stockage durable.
- Consolidation Compose sous l'identité `modern-mlops-2`, deux images non-root et groupes
  de dépendances séparés ; aucun changement dans le dépôt original `modern-mlops`.
- CI avec PostgreSQL isolé, audit et scans, release GHCR sur tags, Dependabot, scripts
  d'exercices, test de charge, runbook et audit des 22 étapes.

## Validation locale

- 38 tests réussis avec PostgreSQL et Feast réels ; Ruff et vérification du format réussis.
- Jobs training/monitoring, promotion, smoke authentifié et scraping validés dans Compose.
- Modèle : R² 0,845 ; RMSE holdout 31 823 ; 1 110 ventes anciennes pour entraîner,
  350 ventes plus récentes pour tester, sans mois partagé.
- Gate alpha=1000 refusée, promotion d'une version rejetée refusée, promotion/rollback
  confirmés par les versions servies ; données corrompues arrêtées avant entraînement.
- Prix ×1,6 : échec de qualité et run Dagster rouge ; panne PostgreSQL : prédiction
  maintenue, alerte Prometheus firing, puis reprise du stockage.
- Grafana : six panneaux, deux sources opérationnelles et accès SQL en lecture seule.
- Charge : 20 utilisateurs pendant deux minutes, zéro erreur, p95 25 ms ; objectif de
  laboratoire mesuré dans cette session, pas une garantie de production.
- Sauvegarde PostgreSQL restaurée dans une base distincte (8 117 prédictions à cet instant) ;
  neuf fichiers d'artefacts MLflow restaurés avec checksums identiques.
- Arrêt complet sans suppression de volumes, redémarrage, champion et smoke revalidés.
- Audit Python : aucune vulnérabilité connue ; scan API : zéro HIGH/CRITICAL corrigeable.
  Le scan pipeline informatif rapporte 81 occurrences corrigeables (77 HIGH, 4 CRITICAL)
  dans les JAR Spark. Elles restent à traiter avant un usage en production ; détails
  et versions corrigées dans l'audit et les preuves.

## Limites de validation

L'accès OpenML direct est refusé par la politique réseau du cloud : le même jeu Ames a été
testé via un miroir HTTPS explicite, fixé à un commit et vérifié par SHA-256. Aucun repli
silencieux sur du synthétique. Les extensions d'un IDE local ne sont pas vérifiables ici.
Les exécutions Actions et la publication GHCR doivent être observées sur GitHub ; aucune
release n'a été publiée pendant cette tâche. Voir `docs/TP_AUDIT.md` pour le statut précis
de chaque étape et `docs/TP_EVIDENCE.json` pour les résultats conservés.
