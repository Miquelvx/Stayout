### ======== STAYOUT - Race Analysis ======== ### 

# ----------------------------
# IMPORTATIONS DES LIBRAIRIES
# ----------------------------
import streamlit as st
import fastf1
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os

import plotly.graph_objects as go

from Code.fonctions_get_data import get_calendar,get_race_session, calculate_race_metrics
from Code.fonctions_create_plot import create_lap_chart
from Code.constants import DRAPEAUX_EMOJI

# ----------------------------
# CONFIG
# ----------------------------

st.set_page_config(page_title="Stayout - Analyse de course", layout="wide")


# ----------------------------
# MAIN RACE ANALYSIS PAGE
# ----------------------------

def main():

    st.title("Analyse de course 🏁")

    st.markdown("#### ⚔️ Duel en Piste : Analyse des Dépassements")
    st.markdown("Au-delà de la vitesse pure, la capacité à gagner des positions est la clé du résultat final. Cette page analyse l'intégralité des manœuvres effectuées durant le Grand Prix :")
    st.markdown("""
    - Dépassement en 1v1 (échange de position entre deux pilotes)
    - Bataille entre plusieurs pilotes.
    - Impact des stratégies avec les arrêts au stand. 
    """) 

    st.divider()

    if 'actual_year' in st.session_state:
        actual_year = st.session_state['actual_year']

        # --- SIDEBAR ---
        with st.sidebar:
            st.markdown ("Filtre ⚙️")

            st.markdown(" *Configure tes données avec ce panel de configuration.* ")

            annee = st.select_slider(
                "Selectionner l'année de la saison 📅",
                options=[actual_year-4,actual_year-3,actual_year-2, actual_year-1, actual_year],
                value=actual_year
            )
            if annee == actual_year and 'df_calendar{actual_year}' in st.session_state:
                df_calendar = st.session_state['df_calendar{actual_year}']
            else:
                df_calendar = get_calendar(annee)

            df_gp_only = df_calendar[df_calendar['EventName'].str.contains('Grand Prix', na=False)].copy()
            df_gp_only['EventNameWithFlag'] = df_gp_only.apply(
                lambda row: f"{DRAPEAUX_EMOJI.get(row['Country'], '🏁')} {row['EventName']}", axis=1
            )
            grand_prix = st.selectbox("Selectionner le grand prix 🏆", df_gp_only['EventNameWithFlag'])
            selected_gp_row = df_gp_only[df_gp_only['EventNameWithFlag'] == grand_prix].iloc[0]
            round_number = selected_gp_row['RoundNumber']

        session = get_race_session(annee, round_number)
        
        if not session.results.empty:
            fig = create_lap_chart(session)

            st.plotly_chart(fig, use_container_width=True)

            # --- Affichage Streamlit ---
            total_ov, dnfs, top_ov = calculate_race_metrics(session)

            st.markdown("""
                <style>
                    /* Cibler le conteneur du widget metric */
                    [data-testid="stMetric"] {
                        background-color: #15151e;
                        border-left: 5px solid #e10600;
                        padding: 15px;
                        border-radius: 10px;
                        
                        /* --- FORCER LA TAILLE UNIFORME --- */
                        height: 120px; /* Ajuste cette valeur selon tes besoins */
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                    }

                    [data-testid="stMetricLabel"] {
                        color: #949498 !important;
                        font-family: 'Titillium Web', sans-serif;
                        font-size: 0.85em !important;
                        text-transform: uppercase;
                        white-space: nowrap; /* Évite que le titre ne passe à la ligne */
                    }

                    [data-testid="stMetricValue"] {
                        color: white !important;
                        font-family: 'Titillium Web', sans-serif;
                        font-weight: bold;
                        font-size: 1.8em !important;
                    }
                    
                    /* Cibler la petite légende sous la valeur (le delta) */
                    [data-testid="stMetricDelta"] {
                        font-family: 'Titillium Web', sans-serif;
                    }
                </style>
                """, unsafe_allow_html=True)

            # Affichage
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Dépassements", f" {total_ov}")
            col2.metric("Abandons (DNF)", f"❌ {dnfs}")
            col3.metric("Roi du dépassement", top_ov['Driver'], f"🔥 {top_ov['Overtakes']} fois")
        else:
            st.info("La course n'a pas encore eu lieu")
    else :
        st.warning("Veuillez repasser par la page d'accueil")

if __name__ == "__main__":
    main()