"""Interface de recueil — Étape 2 : champs spécifiques à chaque pathologie.

Lancer avec :  streamlit run app.py
"""
from datetime import date

import streamlit as st

import db


# --- Champs spécifiques : une fonction par pathologie -----------------------------
# Chacune affiche ses widgets et renvoie un dict dont les clés = colonnes de sa table.

def champs_avc() -> dict:
    c1, c2, c3 = st.columns(3)
    return {
        "type_avc": c1.selectbox("Type d'AVC", db.TYPES_AVC, index=None),
        "nihss_admission": c2.number_input(
            "NIHSS à l'admission", min_value=0, max_value=42, value=None, step=1),
        "rankin_sortie": c3.number_input(
            "Rankin modifié à la sortie", min_value=0, max_value=6, value=None, step=1),
        "thrombolyse": c1.checkbox("Thrombolyse IV"),
        "thrombectomie": c2.checkbox("Thrombectomie mécanique"),
    }


def champs_idm() -> dict:
    c1, c2, c3 = st.columns(3)
    return {
        "type_idm": c1.selectbox("Type d'infarctus", db.TYPES_IDM, index=None),
        "killip": c2.selectbox("Classe Killip", db.CLASSES_KILLIP, index=None),
        "fevg": c3.number_input("FEVG (%)", min_value=5, max_value=85, value=None, step=1),
        "thrombolyse_prehosp": c1.checkbox("Thrombolyse préhospitalière"),
        "angioplastie_primaire": c2.checkbox("Angioplastie primaire"),
    }


def champs_coro() -> dict:
    c1, c2, c3 = st.columns(3)
    return {
        "indication": c1.selectbox("Indication", db.INDICATIONS_CORO, index=None),
        "voie_abord": c2.selectbox("Voie d'abord", db.VOIES_ABORD, index=None),
        "nb_vaisseaux": c3.number_input(
            "Vaisseaux atteints", min_value=0, max_value=3, value=None, step=1),
        "angioplastie": c1.checkbox("Angioplastie réalisée"),
        "nb_stents": c2.number_input("Nombre de stents", min_value=0, max_value=10, value=0, step=1),
        "complication": c3.checkbox("Complication"),
    }


CHAMPS_SPECIFIQUES = {
    "AVC": champs_avc,
    "Infarctus du myocarde": champs_idm,
    "Coronarographie / angioplastie": champs_coro,
}


def erreurs_details(pathologie: str, d: dict) -> list[str]:
    """Contrôles de complétude et de cohérence clinique propres à chaque pathologie."""
    erreurs = []
    if pathologie == "AVC":
        if d["type_avc"] is None:
            erreurs.append("Précise le type d'AVC.")
        if d["type_avc"] == "Hémorragique" and d["thrombolyse"]:
            erreurs.append("Thrombolyse saisie pour un AVC hémorragique : vérifie la saisie.")
    elif pathologie == "Infarctus du myocarde":
        if d["type_idm"] is None:
            erreurs.append("Précise STEMI ou NSTEMI.")
        if d["type_idm"] == "NSTEMI" and d["angioplastie_primaire"]:
            erreurs.append("L'angioplastie primaire concerne le STEMI : vérifie la saisie.")
    else:  # Coronarographie / angioplastie
        if d["indication"] is None:
            erreurs.append("Précise l'indication de la coronarographie.")
        if d["nb_stents"] > 0 and not d["angioplastie"]:
            erreurs.append("Des stents sont saisis sans angioplastie cochée.")
        if d["angioplastie"] and d["nb_vaisseaux"] == 0:
            erreurs.append("Angioplastie cochée alors qu'aucun vaisseau n'est atteint.")
    return erreurs


# --- Page -------------------------------------------------------------------------
st.set_page_config(page_title="Parcours de soins", layout="wide")
db.init_db()

st.title("Recueil – parcours de soins cardio-neurovasculaires")
st.caption("Données fictives uniquement à ce stade. Aucun nom ni date de naissance complète.")

onglet_saisie, onglet_liste = st.tabs(["Nouvelle prise en charge", "Prises en charge"])

# --- Saisie -----------------------------------------------------------------------
with onglet_saisie:
    # La pathologie est choisie HORS du formulaire : dans un st.form, changer
    # une valeur ne relance pas le script, donc le reste du formulaire
    # ne pourrait pas s'adapter. Hors formulaire, chaque choix relance le script.
    pathologie = st.selectbox("Pathologie / acte", db.PATHOLOGIES, index=None)

    if pathologie is None:
        st.info("Choisis d'abord la pathologie ou l'acte : le formulaire s'adapte à ce choix.")
    else:
        # clear_on_submit=False : sinon les champs seraient vidés même quand la
        # validation échoue, et il faudrait tout ressaisir.
        with st.form("saisie", clear_on_submit=False):
            st.subheader("Patient")
            c1, c2, c3 = st.columns(3)
            code_patient = c1.text_input("Code patient (pseudonyme)", placeholder="ex. P-0001")
            annee_naissance = c2.number_input(
                "Année de naissance", min_value=1900, max_value=date.today().year,
                value=None, step=1,
            )
            sexe = c3.radio("Sexe", db.SEXES, horizontal=True, index=None)

            st.subheader("Séjour")
            c1, c2, c3, c4 = st.columns(4)
            date_admission = c1.date_input("Date d'admission", value=date.today(), format="DD/MM/YYYY")
            date_sortie = c2.date_input("Date de sortie", value=None, format="DD/MM/YYYY")
            mode_sortie = c3.selectbox("Mode de sortie", db.MODES_SORTIE)
            etablissement = c4.selectbox("Établissement", db.ETABLISSEMENTS, index=None)

            st.subheader(f"Spécifique – {pathologie}")
            details = CHAMPS_SPECIFIQUES[pathologie]()

            envoye = st.form_submit_button("Enregistrer", type="primary")

        if envoye:
            # Validation : on accumule toutes les erreurs pour les afficher en une fois.
            erreurs = []
            if not code_patient.strip():
                erreurs.append("Le code patient est obligatoire.")
            if date_sortie and date_sortie < date_admission:
                erreurs.append("La date de sortie est antérieure à la date d'admission.")
            if mode_sortie != "En cours" and date_sortie is None:
                erreurs.append("Un mode de sortie est renseigné sans date de sortie.")
            if etablissement is None:
                erreurs.append("Choisis l'établissement.")
            erreurs += erreurs_details(pathologie, details)

            if erreurs:
                for e in erreurs:
                    st.error(e)
            else:
                db.ajouter_prise_en_charge(
                    {
                        "code_patient": code_patient.strip().upper(),
                        "annee_naissance": annee_naissance,
                        "sexe": sexe,
                        "pathologie": pathologie,
                        "date_admission": date_admission.isoformat(),
                        "date_sortie": date_sortie.isoformat() if date_sortie else None,
                        "mode_sortie": mode_sortie,
                        "etablissement": etablissement,
                    },
                    details,
                )
                st.success(f"Prise en charge enregistrée pour {code_patient.strip().upper()}.")

# --- Liste ------------------------------------------------------------------------
with onglet_liste:
    filtre = st.selectbox("Filtrer par pathologie", ["Toutes"] + db.PATHOLOGIES)
    lignes = db.lister_prises_en_charge(None if filtre == "Toutes" else filtre)

    st.metric("Prises en charge", len(lignes))
    if filtre == "Toutes":
        st.caption("Choisis une pathologie pour afficher aussi ses champs spécifiques.")
    if lignes:
        st.dataframe(lignes, width="stretch", hide_index=True)
    else:
        st.info("Aucune prise en charge enregistrée. Utilise l'onglet « Nouvelle prise en charge ».")