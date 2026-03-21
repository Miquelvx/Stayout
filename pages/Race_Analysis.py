import streamlit as st
import fastf1
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os

import plotly.graph_objects as go

from Code.fonctions_get_data import get_calendar,get_race_session, calculate_race_metrics
from Code.fonctions_create_plot import create_lap_chart

# ----------------------------
# CONFIG
# ----------------------------

st.set_page_config(page_title="StayOut - Race Analysis", layout="wide")


# ----------------------------
# MAIN RACE ANALYSIS PAGE
# ----------------------------

def main():

    st.title("Race analysis")

    if 'actual_year' in st.session_state:
        actual_year = st.session_state['actual_year']

        # --- SIDEBAR ---

        with st.sidebar:
            st.text("Filtre")

            annee = st.select_slider(
                "Selectionner l'année de la saison",
                options=[actual_year-4,actual_year-3,actual_year-2, actual_year-1, actual_year],
                value=actual_year
            )
            if annee == actual_year and 'df_calendar{actual_year}' in st.session_state:
                df_calendar = st.session_state['df_calendar{actual_year}']
            else:
                df_calendar = get_calendar(annee)

            df_gp_only = df_calendar[df_calendar['EventName'].str.contains('Grand Prix', na=False)]
            grand_prix = st.selectbox("Selectionner le grand prix", df_gp_only['EventName'])
            selected_gp_row = df_gp_only[df_gp_only['EventName'] == grand_prix].iloc[0]
            round_number = selected_gp_row['RoundNumber']

        session = get_race_session(annee, round_number)

        if not session.results.empty:
            fig = create_lap_chart(session)

            st.plotly_chart(fig, use_container_width=True)

            # --- Affichage Streamlit ---
            total_ov, dnfs, top_ov = calculate_race_metrics(session)

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Dépassements", total_ov)
            col2.metric("Abandons (DNF)", dnfs)
            col3.metric("Roi du dépassement", top_ov['Driver'], f"{top_ov['Overtakes']} fois")
        else:
            st.info("La course n'a pas encore eu lieu")
    
    else :
        st.warning("Veuillez repasser par la page d'accueil")


if __name__ == "__main__":
    main()