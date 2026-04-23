### ======== STAYOUT - Fonctions Get Data ======== ### 

# ----------------------------
# IMPORTATIONS DES LIBRAIRIES
# ----------------------------
import streamlit as st
import fastf1
import pandas as pd
import numpy as np

from Code.constants import TEAM_COLORS, DRAPEAUX

# Récupération calendrier F1
def get_calendar(year):
    with st.spinner("Récupération du calendrier F1..."):
        calendar = fastf1.get_event_schedule(year)
        df_calendar = calendar.copy()

        colonnes = [
            'RoundNumber','Country','Location','EventDate','EventName',
            'EventFormat','Session1','Session1DateUtc','Session2',
            'Session2DateUtc','Session3','Session3DateUtc','Session4',
            'Session4DateUtc','Session5','Session5DateUtc'
        ]
        
        df_calendar = df_calendar[colonnes]
        sessions_cols = ['Session1DateUtc', 'Session2DateUtc', 'Session3DateUtc','Session4DateUtc', 'Session5DateUtc']
        df_calendar['EventDate'] = pd.to_datetime(df_calendar['EventDate'])
        
        for col in sessions_cols:
            df_calendar[col] = (pd.to_datetime(df_calendar[col], utc=True).dt.tz_convert("Europe/Paris")).dt.tz_localize(None)
    return df_calendar

# Récupération session de course
def get_race_session(year, round_num):
    with st.spinner("Chargement de la course..."):
        sess = fastf1.get_session(year, round_num, 'R')
        sess.load(telemetry=True, weather=False, messages=False)
    return sess

# Récupération session qualification
def get_qualif_session(year, round_num):
    with st.spinner("Chargement de la qualification..."):
        sess = fastf1.get_session(year, round_num, 'Q')
        sess.load(telemetry=True, weather=False, messages=False)
    return sess

# Calcul classement pilotes / écuries
def get_current_standings(actual_date):
    with st.spinner("Calcul des classements F1..."):
        drivers_df = pd.DataFrame()
        constructors_df = pd.DataFrame()
        drivers_data = {}
        constructors_data = {}

        df_calendar = get_calendar(actual_date.year)
        
        try:
            cond_sprint = (df_calendar['EventFormat'] == 'sprint_qualifying')
            cond_conv = (df_calendar['EventFormat'] == 'conventional')

            reference_date = np.select(
                [cond_sprint, cond_conv], 
                [df_calendar['Session3DateUtc'], df_calendar['Session5DateUtc']], 
                default=df_calendar['Session5DateUtc'] )
            completed_events = df_calendar[reference_date <= actual_date]
            for _, event in completed_events.iterrows():
                try:
                    # Chargement des résultats de la course
                    session = fastf1.get_session(actual_date.year, event['RoundNumber'], 'R')
                    session.load(telemetry=False, weather=False, messages=False)
                    if hasattr(session, 'results'):
                        for _, row in session.results.iterrows():
                            abb = row['Abbreviation']
                            team = row['TeamName']
                            pts = row['Points']
                            
                            # Pilotes
                            if abb not in drivers_data:
                                drivers_data[abb] = {'Pilote': row['FullName'], 'Ecurie': team, 'Points': 0.0}
                            drivers_data[abb]['Points'] += pts
                                
                            # Constructeurs
                            if team not in constructors_data:
                                constructors_data[team] = {'Ecurie': team, 'Points': 0.0}
                            constructors_data[team]['Points'] += pts
                    # Gestion des points Sprint
                    if event['Session3'] == 'Sprint':
                        s_sess = fastf1.get_session(actual_date.year, event['RoundNumber'], 'S')
                        s_sess.load(telemetry=False, weather=False, messages=False)
                        if hasattr(s_sess, 'results'):
                            for _, row in s_sess.results.iterrows():
                                abb = row['Abbreviation']
                                team = row['TeamName']
                                pts = row['Points']
                                if abb in drivers_data: drivers_data[abb]['Points'] += pts
                                if team in constructors_data: constructors_data[team]['Points'] += pts   
                except Exception:
                    continue
            # Création des DataFrames finaux
            if drivers_data:
                drivers_df = pd.DataFrame(drivers_data.values())
                drivers_df = drivers_df.sort_values(by=['Points'], ascending=False).reset_index(drop=True)
                drivers_df['Pos'] = drivers_df.index + 1
                drivers_df = drivers_df[['Pos', 'Pilote', 'Ecurie', 'Points']]
            if constructors_data:
                constructors_df = pd.DataFrame(constructors_data.values())
                constructors_df = constructors_df.sort_values(by=['Points'], ascending=False).reset_index(drop=True)
                constructors_df['Pos'] = constructors_df.index + 1
                constructors_df = constructors_df[['Pos', 'Ecurie', 'Points']]
        except Exception as e:
            st.error(f"Erreur lors de la récupération des classements : {e}")
    return drivers_df, constructors_df

# Calcul statistiques de course
def calculate_race_metrics(_session):
    with st.spinner("Calcul des statistiques de la course..."):
        total_race_overtakes = 0
        driver_stats = []
        for driver_id in _session.drivers:
            driver_info = _session.get_driver(driver_id)
            abb = driver_info['Abbreviation']
            statut = driver_info['Status']
            grid_pos = int(driver_info['GridPosition'])
            driver_overtakes = 0
            net_gain = 0
            # On récupère les tours
            laps = _session.laps.pick_driver(abb)
            if not laps.empty:
                # Calcul des dépassements tour par tour
                pos_series = [grid_pos] + laps['Position'].tolist()
                if len(pos_series) > 1:
                    for i in range(len(pos_series) - 1):
                        diff = pos_series[i] - pos_series[i+1]
                        if diff > 0:
                            driver_overtakes += diff
                start_pos = driver_info['GridPosition']
                end_pos = driver_info['Position']
                net_gain = start_pos - end_pos 
            else:
                net_gain = 0
                driver_overtakes = 0
            total_race_overtakes +=  int(driver_overtakes)
            driver_stats.append({
                'Driver': abb,
                'Overtakes': int(driver_overtakes),
                'NetGain': net_gain,
                'Status': statut
            })
        # Conversion en DataFrame
        df_stats = pd.DataFrame(driver_stats)
        if not df_stats.empty and df_stats['Overtakes'].max() > 0:
            best_overtaker = df_stats.loc[df_stats['Overtakes'].idxmax()]
        else:
            best_overtaker = {'Driver': 'N/A', 'Overtakes': 0}
        num_dnf = len(df_stats[~df_stats['Status'].str.contains('Finished|Lapped')])
    return total_race_overtakes, num_dnf, best_overtaker

# Récupération infos circuit (Numéro virage)
def get_circuit_corners(_session):
    try:
        # Récupération infos du circuit
        circuit_info = _session.get_circuit_info()
        corners = circuit_info.corners
        return corners
    except Exception:
        return None

# Récupération télémétries pilote
def get_drivers_telemetry(_session, selected_drivers):
    with st.spinner("Récupération des meilleurs tours..."):
        telemetry_dict = {}
        for abb in selected_drivers:
            # Récupération meilleur tour du pilote
            laps_driver = _session.laps.pick_driver(abb)
            fastest_lap = laps_driver.pick_fastest()
            # Extraction télémétrie + distance
            telemetry = fastest_lap.get_telemetry().add_distance()
            # Stockage temps
            lap_time = fastest_lap['LapTime']
            # Formatage temps
            str_lap_time = str(lap_time)[10:19] 
            telemetry_dict[abb] = {
                'telemetry': telemetry,
                'lap_time': str_lap_time,
                'team': fastest_lap['Team']
            }
        return telemetry_dict
    
# Récupération emoji drapeau
def get_flag_emoji(country):
    iso_code = DRAPEAUX.get(country, "un")
    return f"https://flagcdn.com/h40/{iso_code}.png"