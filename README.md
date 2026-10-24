# Recueil – parcours de soins cardio-neurovasculaires

Application Streamlit de saisie et de consultation des prises en charge hospitalières (AVC, infarctus du myocarde, coronarographie / angioplastie). Les données sont stockées dans une base SQLite locale.

> ⚠️ **Données fictives uniquement** à ce stade. Ne saisir ni nom, ni date de naissance complète : le patient est identifié par un pseudonyme (ex. `P-0001`) et son année de naissance.

## Fonctionnalités

- **Nouvelle prise en charge** : formulaire de saisie d'un épisode de soins (patient, pathologie, dates d'admission et de sortie, mode de sortie, établissement), avec validation :
  - code patient, pathologie et établissement obligatoires ;
  - la date de sortie ne peut pas précéder la date d'admission ;
  - un mode de sortie autre que « En cours » exige une date de sortie.
- **Prises en charge** : liste des épisodes enregistrés, filtrable par pathologie, triée de la plus récente à la plus ancienne.

## Prérequis

- Python 3.10 ou plus récent
- [Streamlit](https://streamlit.io/)

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

L'application s'ouvre dans le navigateur (par défaut sur <http://localhost:8501>). La base `parcours.db` est créée automatiquement au premier lancement.

## Structure du projet

| Fichier            | Rôle                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------ |
| `app.py`           | Interface Streamlit : formulaire de saisie et liste des prises en charge                   |
| `db.py`            | Accès à la base SQLite et listes de valeurs autorisées (pathologies, modes de sortie, établissements) |
| `requirements.txt` | Dépendances Python                                                                         |
| `parcours.db`      | Base de données générée à l'exécution (non versionnée)                                     |

## Modèle de données

Une seule table, `prises_en_charge` : une ligne correspond à un épisode de soins (une hospitalisation) pour un patient.

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

Les listes de valeurs proposées dans l'interface (`PATHOLOGIES`, `SEXES`, `MODES_SORTIE`, `ETABLISSEMENTS`) sont définies une seule fois dans `db.py`. Pour en ajouter, il suffit de modifier ces listes.
