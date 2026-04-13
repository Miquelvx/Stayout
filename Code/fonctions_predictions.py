import os
import fastf1
import requests
import pandas as pd
import numpy as np
import streamlit as st
from sklearn.preprocessing import LabelEncoder

from Code.constants import CIRCUITS_GPS

api_key = st.secrets["api_keys"]["openweathermap"]

if 'constructors_df' in st.session_state:
    constructors_df = st.session_state['constructors_df']

# Fonction récupération classement écurie
def get_constructor_standings(session):
    results = session.results
    # On groupe par équipe et on somme les points
    team_points = results.groupby('TeamName')['Points'].sum().sort_values(ascending=False)
    
    standings = {team: pos + 1 for pos, team in enumerate(team_points.index)}
    return standings

# Fonction récupération Top Speed en qualification
def get_top_speed(session_qualif, driver_abb):
    try:
        # On récupère tous les tours du pilote
        laps = session_qualif.laps.pick_driver(driver_abb)
        
        car_data = laps.get_car_data()
        
        if not car_data.empty:
            return car_data['Speed'].max()
        return 0
    except Exception:
        return 0

# Fonction récupération prévisions météo 
def get_weather_forecast(lat, lon, api_key, session_date):
    try:
        #/forecast = prédictions futures
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        response = requests.get(url).json()
        
        target_time = session_date.timestamp()

        best_match = min(response['list'], key=lambda x: abs(target_time - x['dt']))

        air_temp = best_match['main']['temp']
        clouds = best_match['clouds']['all']
        track_temp_est = air_temp + (20 if clouds < 20 else 8)
        
        rain_proba = 1 if "Rain" in best_match['weather'][0]['main'] or best_match.get('pop', 0) > 0.3 else 0
        
        print(f"☀️ Météo trouvée pour {best_match['dt_txt']} (Cible GP: {session_date})")
        return air_temp.round(2), track_temp_est.round(2), rain_proba

    except Exception as e:
        print(f"Erreur API Forecast : {e}")
        return 20.0, 30.0, 0

# Fonction récupération données météo en fonction du gp
def get_weather_data_after_race(session, api_key=None, coords=None):
    # Si la session est à venir -> récupération météo future API
    try:
        session.load(laps=False, telemetry=False, weather=True)
    except Exception as e:
        print(f"Erreur lors du chargement de la session : {e}")
        return None
    
    print("Récupération météo réelle via FastF1...")
    weather = session.weather_data
    return (
        weather['AirTemp'].mean().round(2), 
        weather['TrackTemp'].mean().round(2), 
        int(weather['Rainfall'].any())
    )
    
# Fonction récupération données météo en fonction du gp
def get_weather_data_after_qualif(session, api_key=None, coords=None):
    print("Récupération prévisions via API (Futur)...")
    # Note : utilisez session.date uniquement après le .load()
    return get_weather_forecast(coords['lat'], coords['lon'], api_key, session.date)

    
# Fonction initialisation dataframe
def initialize_feature_df_race(year, round_number):
    # 1. Chargement des sessions
    session_race = fastf1.get_session(year, round_number, 'R')
    session_qualif = fastf1.get_session(year, round_number, 'Q')

    session_race.load(laps=True, telemetry=False, weather=True, messages=False) 
    session_qualif.load(laps=True, telemetry=True, weather=True, messages=False)
    
    # 2. Récupération des résultats de course
    results_race = session_race.results.copy()
    
    ## Sélection des colonnes
    results_columns = ['Abbreviation', 'TeamName', 'GridPosition', 'Position']
    df_feature = results_race[results_columns].copy()
    df_feature['last_qualif_pos'] = df_feature['GridPosition']
    df_feature['EventName'] = session_race.event['EventName']
    df_feature['RoundNumber'] = round_number
    df_feature['Year'] = year

    df_feature.rename(columns={
        'GridPosition': 'qualif_pos',
        'Position': 'race_finish_pos'
    }, inplace=True)

    df_feature['is_race_incident'] = ~results_race['Status'].str.contains('Finished|Lap', na=False)
    df_feature['is_race_incident'] = df_feature['is_race_incident'].astype(int)

    ## Récupération des données météo
    print(df_feature)
    coords = CIRCUITS_GPS.get(df_feature['EventName'].iloc[0], {'lat': 0, 'lon': 0})
    air_temp, track_temp, rain_proba = get_weather_data_after_race(session_race, api_key, coords)

    # 3. Traitement des données de qualifications
    laps_qualif = session_qualif.laps

    fastest_laps = laps_qualif.groupby('Driver').apply(lambda x: x.pick_fastest())
    fastest_laps = fastest_laps[['Driver', 'LapTime']].reset_index(drop=True)
    fastest_laps['LapTime'] = fastest_laps['LapTime'].dt.total_seconds()

    # 4. Fusion des données de qualification dans le dataframe
    df_feature = df_feature.merge(
        fastest_laps,
        left_on='Abbreviation',
        right_on='Driver',
        how='left'
    )

    # 5. Calculs des métriques de performance
    df_feature.rename(columns={'LapTime': 'qualif_time'}, inplace=True)
    
    ## Temps de la pole position
    pole_time = df_feature['qualif_time'].min()
    
    ## Gap from pole en pourcentage
    df_feature['GapFromPole_pct'] = (((df_feature['qualif_time'] - pole_time) / pole_time) * 100).round(3)

    ## Sécurité DNF/DNQ/DNS pendant les qualifications
    df_feature['is_incident_quali'] = df_feature['qualif_time'].isna().astype(int)
    df_feature['qualif_time'] = df_feature['qualif_time'].fillna(df_feature['qualif_time'].max())
    df_feature['GapFromPole_pct'] = df_feature['GapFromPole_pct'].fillna(df_feature['GapFromPole_pct'].max())

    # 6. Récupération Top Speed en qualifications
    df_feature['topspeed_kmh_qualif'] = df_feature['Abbreviation'].apply(lambda x: get_top_speed(session_qualif, x))

    # 7. Position classement équipes
    df_feature['constructor_pos'] = df_feature['TeamName'].map(constructors_df.set_index('Ecurie')['Pos'])
    
    ## Ajout des points d'équipe du dernier gp
    if round_number > 1:
        prev_session = fastf1.get_session(year, round_number - 1, 'R')
        prev_session.load(laps=False, telemetry=False, weather=False)
        team_points_prev = prev_session.results.groupby('TeamName')['Points'].sum()
        df_feature['team_performance_lastgp'] = df_feature['TeamName'].map(team_points_prev).fillna(0)
    else:
        df_feature['team_performance_lastgp'] = 0

    # 8. Ajout données météo
    df_feature['air_temp_forecast'] = air_temp
    df_feature['track_temp_forecast'] = track_temp
    df_feature['rain_proba_forecast'] = rain_proba

    # 9. Nettoyage final
    df_feature.drop(columns=['Driver'], inplace=True)
    df_feature.reset_index(drop=True)

    return df_feature

def initialize_feature_df_qualif(year, round_number):
    # 1. Chargement des sessions
    session_qualif = fastf1.get_session(year, round_number, 'Q')

    session_qualif.load(laps=True, telemetry=True, weather=True, messages=False)
    
    # 2. Récupération des résultats de course
    results_race = session_qualif.results.copy()
    
    ## Sélection des colonnes
    results_columns = ['Abbreviation', 'TeamName', 'Position', 'GridPosition']
    df_feature = results_race[results_columns].copy()
    df_feature['last_qualif_pos'] = df_feature['GridPosition']
    df_feature['EventName'] = session_qualif.event['EventName']
    df_feature['RoundNumber'] = round_number
    df_feature['Year'] = year

    df_feature.rename(columns={
        'GridPosition': 'race_finish_pos',
        'Position': 'qualif_pos'
    }, inplace=True)

    df_feature['is_race_incident'] = ~results_race['Status'].str.contains('Finished|Lap', na=False)
    df_feature['is_race_incident'] = df_feature['is_race_incident'].astype(int)

    ## Récupération des données météo
    coords = CIRCUITS_GPS.get(df_feature['EventName'].iloc[0], {'lat': 0, 'lon': 0})
    air_temp, track_temp, rain_proba = get_weather_data_after_qualif(session_qualif, api_key, coords)

    # 3. Traitement des données de qualifications
    laps_qualif = session_qualif.laps

    fastest_laps = laps_qualif.groupby('Driver').apply(lambda x: x.pick_fastest())
    fastest_laps = fastest_laps[['Driver', 'LapTime']].reset_index(drop=True)
    fastest_laps['LapTime'] = fastest_laps['LapTime'].dt.total_seconds()

    # 4. Fusion des données de qualification dans le dataframe
    df_feature = df_feature.merge(
        fastest_laps,
        left_on='Abbreviation',
        right_on='Driver',
        how='left'
    )

    # 5. Calculs des métriques de performance
    df_feature.rename(columns={'LapTime': 'qualif_time'}, inplace=True)
    
    ## Temps de la pole position
    pole_time = df_feature['qualif_time'].min()
    
    ## Gap from pole en pourcentage
    df_feature['GapFromPole_pct'] = (((df_feature['qualif_time'] - pole_time) / pole_time) * 100).round(3)

    ## Sécurité DNF/DNQ/DNS pendant les qualifications
    df_feature['is_incident_quali'] = df_feature['qualif_time'].isna().astype(int)
    df_feature['qualif_time'] = df_feature['qualif_time'].fillna(df_feature['qualif_time'].max())
    df_feature['GapFromPole_pct'] = df_feature['GapFromPole_pct'].fillna(df_feature['GapFromPole_pct'].max())

    # 6. Récupération Top Speed en qualifications
    df_feature['topspeed_kmh_qualif'] = df_feature['Abbreviation'].apply(lambda x: get_top_speed(session_qualif, x))
    
    # 7. Position classement équipes
    df_feature['constructor_pos'] = df_feature['TeamName'].map(constructors_df.set_index('Ecurie')['Pos'])

    ## Ajout des points d'équipe du dernier gp
    if round_number > 1:
        prev_session = fastf1.get_session(year, round_number - 1, 'R')
        prev_session.load(laps=False, telemetry=False, weather=False)
        team_points_prev = prev_session.results.groupby('TeamName')['Points'].sum()
        df_feature['team_performance_lastgp'] = df_feature['TeamName'].map(team_points_prev).fillna(0)
    else:
        df_feature['team_performance_lastgp'] = 0

    # 8. Ajout données météo
    df_feature['air_temp_forecast'] = air_temp
    df_feature['track_temp_forecast'] = track_temp
    df_feature['rain_proba_forecast'] = rain_proba

    # 9. Nettoyage final
    df_feature.drop(columns=['Driver'], inplace=True)
    df_feature.reset_index(drop=True)

    return df_feature

# 
def calculate_podium_proba(pos):
        # Formule mathématique pour convertir la position en probabilité (0 à 100)
        # On centre la chute de probabilité autour de la 3.5ème place
        proba = 1 / (1 + np.exp((pos - 3.5) * 2))
        return round(proba * 100, 1)


# Fonction save dataframe into csv
def save_to_master_db(df_new, db_path):
    if not os.path.exists(db_path):
        df_new.to_csv(db_path, index=False)
        print(f"📁 Master DB créé avec le Round {df_new['RoundNumber'].iloc[0]}.")
        return

    df_old = pd.read_csv(db_path)
    current_round = df_new['RoundNumber'].iloc[0]
    current_year = df_new['Year'].iloc[0]
    
    is_already_present = ((df_old['RoundNumber'] == current_round) & 
                          (df_old['Year'] == current_year)).any()
    
    if not is_already_present:
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
        df_combined.to_csv(db_path, index=False)
        print(f"✅ GP {current_round} ({current_year}) ajouté avec succès.")
    else:
        print(f"ℹ️ Le GP {current_round} ({current_year}) est déjà dans la base. Pas d'ajout.")

def encoding_label(df_master, df_next_gp):
    df_combined = pd.concat([df_master, df_next_gp], ignore_index=True)
    
    # 3. Encoder sur la base du combiné
    encoders = {}
    cols_to_encode = ['Abbreviation', 'TeamName', 'EventName']

    for col in cols_to_encode:
        le = LabelEncoder()
        # On 'fit' sur TOUTES les valeurs possibles
        le.fit(df_combined[col].astype(str)) 
        
        # On 'transform' séparément les deux DataFrames
        df_master[col] = le.transform(df_master[col].astype(str))
        df_next_gp[col] = le.transform(df_next_gp[col].astype(str))
        
        # On garde l'encodeur en mémoire
        encoders[col] = le
    
    return df_master, df_next_gp, encoders