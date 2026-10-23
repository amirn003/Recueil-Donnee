"""Couche base de données (SQLite).

Étape 1 : une seule table, « prises_en_charge ».
Une ligne = un épisode de soins (une hospitalisation) pour un patient.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "parcours.db"

# Listes de valeurs autorisées : définies une seule fois, réutilisées par l'interface.
PATHOLOGIES = ["AVC", "Infarctus du myocarde", "Coronarographie / angioplastie"]
SEXES = ["F", "H"]
MODES_SORTIE = ["En cours", "Domicile", "SSR / rééducation", "Transfert", "Décès"]
ETABLISSEMENTS = ["CHU de Bordeaux", "CHU de Toulouse", "Gustave Roussy", "CHU de Poitiers" "Autre"]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
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
            )
            """
        )


def ajouter_prise_en_charge(donnees: dict) -> int:
    """Insère un épisode. `donnees` est un dict dont les clés = noms de colonnes."""
    colonnes = [
        "code_patient", "annee_naissance", "sexe", "pathologie",
        "date_admission", "date_sortie", "mode_sortie", "etablissement"
    ]
    valeurs = [donnees.get(c) for c in colonnes]
    requete = (
        f"INSERT INTO prises_en_charge ({', '.join(colonnes)}) "
        f"VALUES ({', '.join('?' for _ in colonnes)})"
    )
    # Les noms de colonnes viennent de NOTRE liste (sûr) ; les valeurs passent par « ? ».
    with get_connection() as conn:
        return conn.execute(requete, valeurs).lastrowid


def lister_prises_en_charge(pathologie: str | None = None) -> list[dict]:
    requete = "SELECT * FROM prises_en_charge"
    params: tuple = ()
    if pathologie:
        requete += " WHERE pathologie = ?"
        params = (pathologie,)
    requete += " ORDER BY date_admission DESC, id DESC"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(requete, params).fetchall()]
