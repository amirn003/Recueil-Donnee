"""Démo : la chaîne complète d'intégration de données avec Streamlit.

Lancer avec :  streamlit run demo.py
Réutilise db.py : les données intégrées ici apparaissent aussi dans app.py.

    1. Importer  →  2. Contrôler / corriger  →  3. Intégrer en base  →  4. Exploiter
"""
import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="Démo intégration", layout="wide")
db.init_db()

# Colonnes spécifiques de chaque pathologie (= colonnes de sa table de détails)
COLONNES_DETAILS = {
    "AVC": ["type_avc", "nihss_admission", "thrombolyse", "thrombectomie", "rankin_sortie"],
    "Infarctus du myocarde": ["type_idm", "killip", "fevg", "thrombolyse_prehosp", "angioplastie_primaire"],
    "Coronarographie / angioplastie": ["indication", "voie_abord", "nb_vaisseaux", "angioplastie",
                                       "nb_stents", "complication"],
}
COLONNES_COMMUNES = ["code_patient", "annee_naissance", "sexe", "pathologie", "date_admission",
                     "date_sortie", "mode_sortie", "etablissement"]
BOOLEENS = {"thrombolyse", "thrombectomie", "thrombolyse_prehosp", "angioplastie_primaire",
            "angioplastie", "complication"}


# --- Règles de qualité : une ligne -> liste d'anomalies ---------------------------
def anomalies(ligne: pd.Series, doublon: bool) -> list[str]:
    a = []
    if pd.isna(ligne["code_patient"]) or not str(ligne["code_patient"]).strip():
        a.append("code patient manquant")
    if ligne["pathologie"] not in db.PATHOLOGIES:
        a.append("pathologie inconnue")
    if ligne["etablissement"] not in db.ETABLISSEMENTS:
        a.append(f"établissement inconnu : « {ligne['etablissement']} »")
    adm = pd.to_datetime(ligne["date_admission"], format="%Y-%m-%d", errors="coerce")
    sor = pd.to_datetime(ligne["date_sortie"], format="%Y-%m-%d", errors="coerce")
    if pd.isna(adm):
        a.append("date d'admission absente ou mal formée (attendu AAAA-MM-JJ)")
    elif pd.notna(sor) and sor < adm:
        a.append("sortie avant admission")
    p = ligne["pathologie"]
    if p == "AVC":
        if pd.isna(ligne["type_avc"]):
            a.append("type d'AVC manquant")
        if pd.notna(ligne["nihss_admission"]) and not 0 <= ligne["nihss_admission"] <= 42:
            a.append("NIHSS hors plage 0-42")
        if ligne["type_avc"] == "Hémorragique" and ligne["thrombolyse"] == 1:
            a.append("thrombolyse sur AVC hémorragique")
    elif p == "Infarctus du myocarde":
        if pd.isna(ligne["type_idm"]):
            a.append("type d'infarctus manquant")
    elif p == "Coronarographie / angioplastie":
        if pd.isna(ligne["indication"]):
            a.append("indication manquante")
        if (ligne["nb_stents"] or 0) > 0 and ligne["angioplastie"] != 1:
            a.append("stents sans angioplastie")
    if doublon:
        a.append("doublon")
    return a


def controler(df: pd.DataFrame) -> pd.DataFrame:
    """Renvoie une copie du tableau avec une colonne « anomalies » en tête."""
    df = df.copy()
    doublons = df.duplicated(subset=["code_patient", "date_admission", "pathologie"], keep="first")
    df.insert(0, "anomalies", [" ; ".join(anomalies(l, d)) for (_, l), d in zip(df.iterrows(), doublons)])
    return df


def propre(v):
    """Valeur pandas -> valeur Python stockable (NaN -> None, 1.0 -> 1)."""
    if pd.isna(v):
        return None
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


# --- Page ---------------------------------------------------------------------------
st.title("Démo – chaîne d'intégration de données")
t_import, t_qualite, t_integrer, t_tableau = st.tabs(
    ["1. Importer", "2. Contrôler et corriger", "3. Intégrer en base", "4. Tableau de bord"])

# 1. IMPORTER ------------------------------------------------------------------------
with t_import:
    st.write("Source : un fichier CSV, par exemple un export d'un autre logiciel.")
    fichier = st.file_uploader("Fichier CSV", type="csv")
    if st.button("…ou charger le fichier d'exemple"):
        fichier = "example_patients.csv"
    if fichier is not None:
        # session_state : le tableau importé survit aux relances du script
        st.session_state["brut"] = pd.read_csv(fichier, dtype={"code_patient": str})
        st.session_state.pop("editeur", None)  # repartir d'un éditeur vierge
    if "brut" in st.session_state:
        brut = st.session_state["brut"]
        st.success(f"{len(brut)} lignes, {len(brut.columns)} colonnes importées.")
        st.dataframe(brut.head(10), hide_index=True)

if "brut" not in st.session_state:
    for onglet in (t_qualite, t_integrer):
        onglet.info("Importe d'abord un fichier dans l'onglet 1.")
    corrige = None
else:
    # 2. CONTRÔLER ET CORRIGER --------------------------------------------------------
    with t_qualite:
        st.write("Corrige directement dans le tableau (double-clic sur une cellule). "
                 "Sélectionne une ligne puis la touche Suppr pour l'effacer (doublon par ex.).")
        # data_editor garde lui-même les modifications : on lui donne toujours le tableau brut.
        corrige = st.data_editor(st.session_state["brut"], key="editeur",
                                 num_rows="dynamic", hide_index=True, height=300)
        controle = controler(corrige)
        en_erreur = controle[controle["anomalies"] != ""]

        c1, c2 = st.columns(2)
        c1.metric("Lignes valides", len(controle) - len(en_erreur))
        c2.metric("Lignes en anomalie", len(en_erreur))
        if len(en_erreur):
            st.dataframe(en_erreur[["anomalies", "code_patient", "pathologie", "date_admission",
                                    "etablissement"]], hide_index=True)
        else:
            st.success("Aucune anomalie : le fichier est prêt à être intégré.")

    # 3. INTÉGRER EN BASE -------------------------------------------------------------
    with t_integrer:
        valides = controle[controle["anomalies"] == ""]
        # Ne pas réintégrer ce qui est déjà en base (clé : patient + date + pathologie)
        en_base = {(l["code_patient"], l["date_admission"], l["pathologie"])
                   for l in db.lister_prises_en_charge()}
        nouvelles = valides[[
            (r.code_patient, r.date_admission, r.pathologie) not in en_base
            for r in valides.itertuples()
        ]]
        st.write(f"**{len(nouvelles)}** lignes valides et nouvelles à intégrer · "
                 f"{len(valides) - len(nouvelles)} déjà en base · "
                 f"{len(controle) - len(valides)} écartées pour anomalie.")
        if st.button("Intégrer en base", type="primary", disabled=len(nouvelles) == 0):
            for _, l in nouvelles.iterrows():
                commun = {c: propre(l[c]) for c in COLONNES_COMMUNES}
                details = {c: propre(l[c]) for c in COLONNES_DETAILS[l["pathologie"]]}
                for c in BOOLEENS & details.keys():
                    details[c] = details[c] or 0
                db.ajouter_prise_en_charge(commun, details)
            st.success(f"{len(nouvelles)} prises en charge intégrées.")
            st.rerun()

# 4. TABLEAU DE BORD (lit la base, pas le fichier) -----------------------------------
with t_tableau:
    base = pd.DataFrame(db.lister_prises_en_charge())
    if base.empty:
        st.info("La base est vide : intègre des données à l'étape 3.")
    else:
        base["date_admission"] = pd.to_datetime(base["date_admission"])
        base["duree"] = (pd.to_datetime(base["date_sortie"]) - base["date_admission"]).dt.days

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prises en charge", len(base))
        c2.metric("Patients distincts", base["code_patient"].nunique())
        c3.metric("Durée moyenne de séjour", f"{base['duree'].mean():.1f} j")
        c4.metric("Mortalité hospitalière", f"{(base['mode_sortie'] == 'Décès').mean():.1%}")

        g1, g2 = st.columns(2)
        g1.subheader("Par pathologie")
        g1.bar_chart(base["pathologie"].value_counts(), horizontal=True)
        g2.subheader("Par établissement")
        g2.bar_chart(base["etablissement"].value_counts(), horizontal=True)

        st.subheader("Admissions par mois")
        par_mois = base.groupby([base["date_admission"].dt.to_period("M").astype(str), "pathologie"]) \
                       .size().unstack(fill_value=0)
        st.bar_chart(par_mois)

        st.download_button("Exporter la base en CSV",
                           base.drop(columns="duree").to_csv(index=False).encode("utf-8"),
                           file_name="export_parcours.csv", mime="text/csv")