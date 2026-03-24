import streamlit as st
import fastf1
import pandas as pd
from datetime import datetime
import os
import time

from Code.fonctions_cache_data import get_cache_size, clear_cache_data
from Code.fonctions_get_data import get_calendar, get_current_standings
from Code.fonctions_create_plot import display_f1_standings
from Code.constants import DRAPEAUX

# ----------------------------
# CONFIG
# ----------------------------

st.set_page_config(page_title="StayOut - Accueil", layout="wide")

if not os.path.exists('f1_cache'):
    os.makedirs('f1_cache')
fastf1.Cache.enable_cache('f1_cache')

st.title("🏎️ StayOut - Dashboard F1")

# ----------------------------
# DATA FETCHING
# ----------------------------

# --- 2. STYLE CSS POUR LA DA F1 ---
st.markdown("""
    <style>
    .f1-container {
        background-color: #15151E;
        padding: 25px;
        border-radius: 15px;
        border-right: 5px solid #FF1801;
        border-bottom: 5px solid #FF1801;
        color: white;
        margin-bottom: 20px;
    }
    .f1-tag {
        background-color: #FF1801;
        color: white;
        padding: 2px 10px;
        font-weight: bold;
        font-size: 0.8em;
        text-transform: uppercase;
        border-radius: 5px;
    }
    .f1-title {
        font-family: 'Arial Black', sans-serif;
        font-size: 2.5em;
        margin: 10px 0;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# ----------------------------
# MAIN STREAMLIT APP
# ----------------------------
def main():
    st.title("🏁 F1 Dashboard 2026")

    with st.sidebar:
        st.divider()
        st.subheader("⚙️ Gestion du Cache")

        cache_path = './f1_cache'

        if os.path.exists(cache_path):
            size = get_cache_size(cache_path)
            st.write(f"Taille du cache disque : **{size:.2f} MO**")
        else:
            st.write("Cache disque : *Non détecté ou vide*")

        if st.button("🗑️ Vider tout le cache", use_container_width=True):
            st.cache_data.clear()
            time.sleep(0.5)
            
            if clear_cache_data(cache_path):
                st.success("Nettoyage effectué.")
                st.rerun()

    # Récupération des données
    now = datetime.now()
    actual_year = now.year
    st.session_state['actual_year'] = actual_year
    actual_date = pd.to_datetime(now.strftime("%Y-%m-%d, %H:%M:%S"))
    st.session_state['actual_date'] = actual_date

    df_calendar = get_calendar(actual_year)
    st.session_state['df_calendar{actual_year}'] = df_calendar
    
    futur_events = df_calendar[df_calendar['Session5DateUtc'] > actual_date]
    
    if not futur_events.empty:
        next_index = futur_events['Session5DateUtc'].idxmin()
        next_event = df_calendar.loc[next_index]

        # Calcul countdown prochaine course
        delta = next_event['Session5DateUtc'] - actual_date
        st.session_state['delta'] = delta 
        jours = delta.days
        heures = delta.seconds // 3600
        nom_gp = next_event['EventName'].upper()
        pays_lieu = f"ROUND {next_event['RoundNumber']} • {next_event['Country']} • {next_event['Location']}"
        iso_code = DRAPEAUX.get(next_event['Country'], "un")  
        url_drapeau = f"https://flagcdn.com/w40/{iso_code}.png"

        sessions_html = ""
        icones = {"Practice 1": "FP1", "Practice 2": "FP2", "Practice 3": "FP3", "Qualifying": "QUAL", "Sprint Qualifying": "SQUAL", "Sprint": "SPRINT", "Race": "RACE"}

        for i in range(1, 6):
            s_name = next_event[f'Session{i}']
            s_date = next_event[f'Session{i}DateUtc'].strftime('%H:%M')
            # On détermine si c'est la course pour mettre un badge rouge
            badge_color = "#FF1801" if i == 5 else "#38383f"
            label_short = icones.get(s_name, s_name[:4].upper())
            
            sessions_html += f"""
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; margin-bottom: 5px; background: #1e1e28; border-radius: 4px; border-left: 3px solid {badge_color};">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span style="background: {badge_color}; color: white; font-size: 0.7em; font-weight: bold; padding: 2px 6px; border-radius: 2px; min-width: 45px; text-align: center;">{label_short}</span>
                    <span style="font-size: 0.9em; font-weight: 500;">{s_name}</span>
                </div>
                <div style="font-family: monospace; font-size: 1.1em; font-weight: bold; color: white;">{s_date}</div>
            </div>
            """
        # --- Affichage prochaine course ---
        st.markdown(f"""
            <div class="f1-container">
                <span class="f1-tag">Next Race</span>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                    <div class="f1-title" style="font-weight: bold; color: white;">
                        {nom_gp} <img src="{url_drapeau}" style="width:40px; margin-right:15px; vertical-align:middle;">
                    </div>
                    <div style="text-align: right; min-width: 120px;">
                        <div style="color: #FF1801; font-size: 2.2em; font-weight: bold; font-family: sans-serif; line-height: 1;">
                            {jours}J {heures}H
                        </div>
                        <div style="color: #949498; font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-top: 5px;">
                            Until Lights Out
                        </div>
                    </div>
                </div>
                <div style=" margin: 15px 0;"></div>
                <details style="cursor: pointer; color: #949498; font-size: 1em;">
                    <summary style="list-style: none; outline: none;">
                        <div style="display: flex; justify-content: space-between; align-items: center; color: #949498; font-size: 1em;">
                            <span>{pays_lieu}</span>
                            <span style="color: #FF1801; font-weight: bold; font-size: 0.8em;">VOIR LE PROGRAMME ▼</span>
                        </div>
                    </summary>
                    <div style="margin-top: 15px;"> {sessions_html} </div>
                </details>
            </div>
        """, unsafe_allow_html=True)

    else:
        st.info("La saison est terminée ! Rendez-vous l'année prochaine.")

    # Affichage du calendrier complet en dessous (optionnel)
    if st.checkbox("Voir tout le calendrier"):
        st.dataframe(df_calendar, use_container_width=True)

    drivers_df, constructors_df = get_current_standings(actual_date)

    display_f1_standings(drivers_df, constructors_df)

if __name__ == "__main__":
    main()

