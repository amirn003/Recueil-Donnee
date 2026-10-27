"""Couche base de données (SQLite).

Étape 2 :
- « prises_en_charge » : les champs communs à toutes les pathologies ;
- une table de détails par pathologie (details_avc, details_idm, details_coro),
  reliée à la prise en charge par une clé étrangère (relation 1-1).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "parcours.db"

# --- Listes de valeurs autorisées -------------------------------------------------
PATHOLOGIES = ["AVC", "Infarctus du myocarde", "Coronarographie / angioplastie"]
SEXES = ["F", "H"]
MODES_SORTIE = ["En cours", "Domicile", "SSR / rééducation", "Transfert", "Décès"]
ETABLISSEMENTS = ["CHU de Bordeaux", "CHU de Toulouse", "Gustave Roussy", "CHU de Poitiers", "Autre"]

TYPES_AVC = ["Ischémique", "Hémorragique", "AIT"]
TYPES_IDM = ["STEMI", "NSTEMI"]
CLASSES_KILLIP = ["I", "II", "III", "IV"]
INDICATIONS_CORO = ["Syndrome coronarien aigu", "Angor stable", "Bilan pré-opératoire", "Autre"]
VOIES_ABORD = ["Radiale", "Fémorale"]

# Pathologie -> table de détails. Sert aussi de liste blanche : seuls ces noms
# de tables peuvent se retrouver dans une requête SQL.
TABLE_DETAILS = {
    "AVC": "details_avc",
    "Infarctus du myocarde": "details_idm",
    "Coronarographie / angioplastie": "details_coro",
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # SQLite ignore les clés étrangères par défaut : il faut les activer à chaque connexion.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS prises_en_charge (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                code_patient     TEXT    NOT NULL,   -- pseudonyme, jamais le nom
                annee_naissance  INTEGER,
                sexe             TEXT,
                pathologie       TEXT    NOT NULL,
                date_admission   TEXT    NOT NULL,   -- format ISO AAAA-MM-JJ
                date_sortie      TEXT,
                mode_sortie      TEXT    NOT NULL DEFAULT 'En cours',
                etablissement    TEXT,
                saisi_le         TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            -- Relation 1-1 : la clé primaire EST la clé étrangère.
            -- Une prise en charge a donc au plus une ligne de détails.
            -- Les CHECK sont une deuxième ligne de défense, après la validation de l'interface.
            CREATE TABLE IF NOT EXISTS details_avc (
                prise_en_charge_id  INTEGER PRIMARY KEY
                                    REFERENCES prises_en_charge(id) ON DELETE CASCADE,
                type_avc            TEXT    NOT NULL,
                nihss_admission     INTEGER CHECK (nihss_admission BETWEEN 0 AND 42),
                thrombolyse         INTEGER NOT NULL DEFAULT 0,   -- booléen : 0 / 1
                thrombectomie       INTEGER NOT NULL DEFAULT 0,
                rankin_sortie       INTEGER CHECK (rankin_sortie BETWEEN 0 AND 6)
            );

            CREATE TABLE IF NOT EXISTS details_idm (
                prise_en_charge_id     INTEGER PRIMARY KEY
                                       REFERENCES prises_en_charge(id) ON DELETE CASCADE,
                type_idm               TEXT    NOT NULL,
                killip                 TEXT,
                fevg                   INTEGER CHECK (fevg BETWEEN 5 AND 85),   -- en %
                thrombolyse_prehosp    INTEGER NOT NULL DEFAULT 0,
                angioplastie_primaire  INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS details_coro (
                prise_en_charge_id  INTEGER PRIMARY KEY
                                    REFERENCES prises_en_charge(id) ON DELETE CASCADE,
                indication          TEXT    NOT NULL,
                voie_abord          TEXT,
                nb_vaisseaux        INTEGER CHECK (nb_vaisseaux BETWEEN 0 AND 3),
                angioplastie        INTEGER NOT NULL DEFAULT 0,
                nb_stents           INTEGER NOT NULL DEFAULT 0 CHECK (nb_stents >= 0),
                complication        INTEGER NOT NULL DEFAULT 0
            );
            """
        )


def _inserer(conn: sqlite3.Connection, table: str, donnees: dict) -> int:
    """INSERT générique. Les noms de colonnes viennent des clés du dict,
    qui sont écrites dans NOTRE code (jamais saisies par l'utilisateur) ;
    les valeurs passent toujours par « ? »."""
    colonnes = list(donnees)
    requete = (
        f"INSERT INTO {table} ({', '.join(colonnes)}) "
        f"VALUES ({', '.join('?' for _ in colonnes)})"
    )
    return conn.execute(requete, list(donnees.values())).lastrowid


def ajouter_prise_en_charge(donnees: dict, details: dict) -> int:
    """Insère la prise en charge ET ses détails dans une seule transaction.

    `with conn` valide (commit) si tout s'est bien passé, et annule tout
    (rollback) à la moindre erreur : on n'aura jamais une prise en charge
    sans ses détails à cause d'un plantage entre les deux INSERT.
    """
    table = TABLE_DETAILS[donnees["pathologie"]]
    with get_connection() as conn:
        pec_id = _inserer(conn, "prises_en_charge", donnees)
        _inserer(conn, table, {"prise_en_charge_id": pec_id, **details})
        return pec_id


def lister_prises_en_charge(pathologie: str | None = None) -> list[dict]:
    """Sans filtre : champs communs uniquement.
    Avec une pathologie : jointure avec sa table de détails."""
    if pathologie:
        table = TABLE_DETAILS[pathologie]
        requete = (
            f"SELECT p.*, d.* FROM prises_en_charge p "
            f"LEFT JOIN {table} d ON d.prise_en_charge_id = p.id "
            f"WHERE p.pathologie = ? "
            f"ORDER BY p.date_admission DESC, p.id DESC"
        )
        params: tuple = (pathologie,)
    else:
        requete = "SELECT * FROM prises_en_charge ORDER BY date_admission DESC, id DESC"
        params = ()
    with get_connection() as conn:
        lignes = [dict(r) for r in conn.execute(requete, params).fetchall()]
    for ligne in lignes:
        ligne.pop("prise_en_charge_id", None)  # doublon de « id » après la jointure
    return lignes