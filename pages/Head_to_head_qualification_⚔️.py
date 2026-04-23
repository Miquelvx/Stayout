### ======== STAYOUT - Head to Head ======== ### 

# ----------------------------
# IMPORTATIONS DES LIBRAIRIES
# ----------------------------
import streamlit as st
import fastf1
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os
import time

import plotly.graph_objects as go

from Code.fonctions_get_data import get_calendar,get_qualif_session,get_drivers_telemetry, get_circuit_corners
from Code.fonctions_create_plot import create_comparison_telemetry, create_pedal_comparison, create_gear_comparison, add_corners_to_fig

from Code.constants import TEAM_COLORS

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Stayout - Telemetry", layout="wide")


def main():
    st.title("Head to head - Qualifications 📊")

    st.markdown("#### ⚔️ Duel entre pilotes : Analyse de la performance sportive")
    st.markdown("Cette page analyse l'intégralité des télémétries des pilotes durant les qualifications des Grand Prix :")
    st.markdown("""
    - Comparaison de vitesse.
    - Analyse de pilotages : Pression accélérateur et freinage.
    - Comparaison des rapports de boite de vitesse.
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

            df_gp_only = df_calendar[df_calendar['EventName'].str.contains('Grand Prix', na=False)]
            grand_prix = st.selectbox("Selectionner le grand prix 🏆", df_gp_only['EventName'])
            selected_gp_row = df_gp_only[df_gp_only['EventName'] == grand_prix].iloc[0]
            round_number = selected_gp_row['RoundNumber']

        session = get_qualif_session(annee, round_number)

        with st.sidebar:
            available_drivers = session.laps['Driver'].unique().tolist()

            available_drivers_formatted = [
                f"{session.get_driver(abb)['FullName']} ({abb})" 
                for abb in available_drivers
            ]

            selected_drivers = st.multiselect(
                "Choisir les pilotes à comparer 🏎️",
                options=available_drivers_formatted,
                default=available_drivers_formatted[:2]
            )

        if not session.results.empty:
            with st.spinner("Chargement des télémétries..."):
                time.sleep(3)
                if selected_drivers:
                    try:
                        corners_info = get_circuit_corners(session)
                        
                        selected_driver = [label.split('(')[-1].replace(')', '') for label in selected_drivers]
                        telemetry_data = get_drivers_telemetry(session, selected_driver)
                        
                        fig_speed = create_comparison_telemetry(telemetry_data)
                        fig_speed_updated = add_corners_to_fig(fig_speed, corners_info)
                        st.plotly_chart(fig_speed_updated, use_container_width=True)

                        fig_pedal = create_pedal_comparison(telemetry_data)
                        fig_pedal_updated = add_corners_to_fig(fig_pedal, corners_info)
                        st.plotly_chart(fig_pedal_updated, use_container_width=True)

                        fig_gear = create_gear_comparison(telemetry_data)
                        fig_gear_updated = add_corners_to_fig(fig_gear, corners_info)
                        st.plotly_chart(fig_gear_updated, use_container_width=True)
                        
                    except Exception as e:
                        st.info(f"Erreur lors du chargement de la télémétrie : {e}")
                else:
                    st.info("Veuillez sélectionner au moins un pilote.")
        else:
            st.info("La course n'a pas encore eu lieu")
    else: 
        st.warning("Veuillez repasser par la page d'accueil")

if __name__ == "__main__":
    main()