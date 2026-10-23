"""Interface de recueil — Étape 1.

Lancer avec :  streamlit run app.py
"""
from datetime import date

import streamlit as st

import db

st.set_page_config(page_title="Parcours de soins", layout="wide")
db.init_db()

st.title("Recueil – parcours de soins cardio-neurovasculaires")
st.caption("Données fictives uniquement à ce stade. Aucun nom ni date de naissance complète.")

onglet_saisie, onglet_liste = st.tabs(["Nouvelle prise en charge", "Prises en charge"])

# --- Saisie ---------------------------------------------------------------------
with onglet_saisie:
    with st.form("saisie", clear_on_submit=True):
        st.subheader("Patient")
        c1, c2, c3 = st.columns(3)
        code_patient = c1.text_input("Code patient (pseudonyme)", placeholder="ex. P-0001")
        annee_naissance = c2.number_input(
            "Année de naissance", min_value=1900, max_value=date.today().year,
            value=None, step=1,
        )
        sexe = c3.radio("Sexe", db.SEXES, horizontal=True, index=None)

        st.subheader("Séjour")
        c1, c2, c3, c4, c5 = st.columns(5)
        pathologie = c1.selectbox("Pathologie / acte", db.PATHOLOGIES, index=None)
        date_admission = c2.date_input("Date d'admission", value=date.today(), format="DD/MM/YYYY")
        date_sortie = c3.date_input("Date de sortie", value=None, format="DD/MM/YYYY")
        mode_sortie = c4.selectbox("Mode de sortie", db.MODES_SORTIE)
        etablissement = c5.selectbox("Établissement", db.ETABLISSEMENTS, index=None)

        envoye = st.form_submit_button("Enregistrer", type="primary")

    if envoye:
        # Validation : on accumule toutes les erreurs pour les affichr en une fois.
        erreurs = []
        if not code_patient.strip():
            erreurs.append("Le code patient est obligatoire.")
        if pathologie is None:
            erreurs.append("Choisis la pathologie ou l'acte.")
        if date_sortie and date_sortie < date_admission:
            erreurs.append("La date de sortie est antérieure à la date d'admission.")
        if mode_sortie != "En cours" and date_sortie is None:
            erreurs.append("Un mode de sortie est renseigné sans date de sortie.")
        if etablissement is None:
            erreurs.append("Choisis l'établissement.")

        if erreurs:
            for e in erreurs:
                st.error(e)
        else:
            db.ajouter_prise_en_charge({
                "code_patient": code_patient.strip().upper(),
                "annee_naissance": annee_naissance,
                "sexe": sexe,
                "pathologie": pathologie,
                "date_admission": date_admission.isoformat(),
                "date_sortie": date_sortie.isoformat() if date_sortie else None,
                "mode_sortie": mode_sortie,
                "etablissement": etablissement,
            })
            st.success(f"Prise en charge enregistrée pour {code_patient.strip().upper()}.")

# --- Liste ----------------------------------------------------------------------
with onglet_liste:
    filtre = st.selectbox("Filtrer par pathologie", ["Toutes"] + db.PATHOLOGIES)
    lignes = db.lister_prises_en_charge(None if filtre == "Toutes" else filtre)

    st.metric("Prises en charge", len(lignes))
    if lignes:
        st.dataframe(lignes, width="stretch", hide_index=True)
    else:
        st.info("Aucune prise en charge enregistrée. Utilise l'onglet « Nouvelle prise en charge ».")
