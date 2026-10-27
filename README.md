# Recueil – parcours de soins cardio-neurovasculaires

Application Streamlit de saisie et de consultation des prises en charge hospitalières (AVC, infarctus du myocarde, coronarographie / angioplastie). Les données sont stockées dans une base SQLite locale.

> ⚠️ **Données fictives uniquement** à ce stade. Ne saisir ni nom, ni date de naissance complète : le patient est identifié par un pseudonyme (ex. `P-0001`) et son année de naissance.

## Fonctionnalités

### Application de saisie (`app.py`)

- **Nouvelle prise en charge** : on choisit d'abord la pathologie ou l'acte, puis le formulaire s'adapte à ce choix. Il comprend :
  - les champs communs : patient (code, année de naissance, sexe) et séjour (dates d'admission et de sortie, mode de sortie, établissement) ;
  - les champs spécifiques à la pathologie (voir [Modèle de données](#modèle-de-données)).

  Contrôles effectués à l'enregistrement (toutes les erreurs sont affichées en une fois, sans vider le formulaire) :
  - code patient et établissement obligatoires ;
  - la date de sortie ne peut pas précéder la date d'admission ;
  - un mode de sortie autre que « En cours » exige une date de sortie ;
  - complétude et cohérence clinique propres à chaque pathologie :
    - **AVC** : type obligatoire ; alerte si thrombolyse sur AVC hémorragique ;
    - **Infarctus** : STEMI / NSTEMI obligatoire ; alerte si angioplastie primaire sur NSTEMI ;
    - **Coronarographie** : indication obligatoire ; alerte si stents sans angioplastie, ou angioplastie sans vaisseau atteint.
- **Prises en charge** : liste des épisodes enregistrés, triée de la plus récente à la plus ancienne. Sans filtre, seuls les champs communs sont affichés ; en filtrant sur une pathologie, ses champs spécifiques apparaissent aussi.

### Démo d'intégration de données (`demo.py`)

Illustre une chaîne complète d'intégration à partir d'un fichier CSV, en quatre onglets :

1. **Importer** : chargement d'un CSV (ou du fichier d'exemple `example_patients.csv`, 80 lignes avec des anomalies volontaires).
2. **Contrôler et corriger** : détection des anomalies ligne par ligne (champs manquants, valeurs inconnues, dates mal formées ou incohérentes, incohérences cliniques, doublons) et correction directe dans le tableau.
3. **Intégrer en base** : seules les lignes valides et absentes de la base (clé : patient + date d'admission + pathologie) sont insérées.
4. **Tableau de bord** : indicateurs (nombre de prises en charge, patients distincts, durée moyenne de séjour, mortalité hospitalière), répartitions par pathologie, établissement et mois, export CSV.

La démo utilise la même base que `app.py` : les données intégrées y apparaissent aussi.

## Prérequis

- Python 3.10 ou plus récent
- [Streamlit](https://streamlit.io/) (installe aussi pandas, utilisé par la démo)

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py     # application de saisie
streamlit run demo.py    # démo d'intégration de données
```

L'application s'ouvre dans le navigateur (par défaut sur <http://localhost:8501>). La base `parcours.db` est créée automatiquement au premier lancement.

> La base n'est pas migrée automatiquement : si un `parcours.db` créé par une version antérieure existe, supprime-le pour repartir sur le nouveau schéma.

## Structure du projet

| Fichier                | Rôle                                                                                                 |
| ---------------------- | ---------------------------------------------------------------------------------------------------- |
| `app.py`               | Interface de saisie : formulaire adapté à la pathologie, contrôles, liste des prises en charge       |
| `demo.py`              | Démo d'intégration : import CSV, contrôle qualité, intégration en base, tableau de bord              |
| `db.py`                | Schéma SQLite, insertion transactionnelle, requêtes, listes de valeurs autorisées                    |
| `example_patients.csv` | Jeu de données fictif pour la démo                                                                   |
| `requirements.txt`     | Dépendances Python                                                                                   |
| `parcours.db`          | Base de données générée à l'exécution (non versionnée)                                               |

## Modèle de données

Une table commune, `prises_en_charge`, plus une table de détails par pathologie, reliée en **relation 1-1** : la clé primaire de la table de détails est aussi une clé étrangère vers `prises_en_charge(id)` (suppression en cascade). La prise en charge et ses détails sont insérés dans une seule transaction.

Les contraintes `CHECK` sur les plages de valeurs constituent une deuxième ligne de défense, après la validation de l'interface. Les booléens sont stockés en `INTEGER` (0 / 1).

### `prises_en_charge` — champs communs

| Colonne           | Type    | Description                                     |
| ----------------- | ------- | ----------------------------------------------- |
| `id`              | INTEGER | Identifiant auto-incrémenté                     |
| `code_patient`    | TEXT    | Pseudonyme du patient (obligatoire)             |
| `annee_naissance` | INTEGER | Année de naissance                              |
| `sexe`            | TEXT    | `F` ou `H`                                      |
| `pathologie`      | TEXT    | Pathologie ou acte (obligatoire)                |
| `date_admission`  | TEXT    | Date ISO `AAAA-MM-JJ` (obligatoire)             |
| `date_sortie`     | TEXT    | Date ISO `AAAA-MM-JJ`                           |
| `mode_sortie`     | TEXT    | Par défaut `En cours`                           |
| `etablissement`   | TEXT    | Établissement de prise en charge                |
| `saisi_le`        | TEXT    | Horodatage de saisie (automatique)              |

### `details_avc` — AVC

| Colonne           | Type    | Description                                 |
| ----------------- | ------- | ------------------------------------------- |
| `type_avc`        | TEXT    | Ischémique, Hémorragique ou AIT (obligatoire) |
| `nihss_admission` | INTEGER | Score NIHSS à l'admission (0 à 42)          |
| `thrombolyse`     | INTEGER | Thrombolyse IV                              |
| `thrombectomie`   | INTEGER | Thrombectomie mécanique                     |
| `rankin_sortie`   | INTEGER | Rankin modifié à la sortie (0 à 6)          |

### `details_idm` — Infarctus du myocarde

| Colonne                 | Type    | Description                         |
| ----------------------- | ------- | ----------------------------------- |
| `type_idm`              | TEXT    | STEMI ou NSTEMI (obligatoire)       |
| `killip`                | TEXT    | Classe Killip (I à IV)              |
| `fevg`                  | INTEGER | FEVG en % (5 à 85)                  |
| `thrombolyse_prehosp`   | INTEGER | Thrombolyse préhospitalière         |
| `angioplastie_primaire` | INTEGER | Angioplastie primaire               |

### `details_coro` — Coronarographie / angioplastie

| Colonne        | Type    | Description                                   |
| -------------- | ------- | --------------------------------------------- |
| `indication`   | TEXT    | Indication de l'examen (obligatoire)          |
| `voie_abord`   | TEXT    | Radiale ou Fémorale                           |
| `nb_vaisseaux` | INTEGER | Nombre de vaisseaux atteints (0 à 3)          |
| `angioplastie` | INTEGER | Angioplastie réalisée                         |
| `nb_stents`    | INTEGER | Nombre de stents posés (≥ 0)                  |
| `complication` | INTEGER | Complication                                  |

Les listes de valeurs proposées dans l'interface (`PATHOLOGIES`, `SEXES`, `MODES_SORTIE`, `ETABLISSEMENTS`, `TYPES_AVC`, `TYPES_IDM`, `CLASSES_KILLIP`, `INDICATIONS_CORO`, `VOIES_ABORD`) sont définies une seule fois dans `db.py`.

### Ajouter une pathologie

1. Dans `db.py` : l'ajouter à `PATHOLOGIES`, créer sa table de détails dans `init_db()` et l'associer à cette table dans `TABLE_DETAILS`.
2. Dans `app.py` : écrire une fonction `champs_<pathologie>()` qui renvoie un dict dont les clés sont les colonnes de la table, l'enregistrer dans `CHAMPS_SPECIFIQUES` et ajouter ses contrôles dans `erreurs_details()`.
3. Dans `demo.py` : déclarer ses colonnes dans `COLONNES_DETAILS` (et `BOOLEENS` le cas échéant), et ses règles dans `anomalies()`.
