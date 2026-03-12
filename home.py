import streamlit as st
import fastf1
import pandas as pd
from datetime import datetime
import os

from Code.fonctions_get_data import get_calendar
from constants import DRAPEAUX

# ----------------------------
# CONFIG
# ----------------------------

st.set_page_config(page_title="StayOut - Accueil", layout="wide")

if not os.path.exists('cache'):
    os.makedirs('cache')
fastf1.Cache.enable_cache('cache')

st.title("🏎️ StayOut - Dashboard F1")

# ----------------------------
# DATA FETCHING
# ----------------------------

@st.cache_data(ttl=3600)
def get_current_standings():
    """Récupère les classements pilotes et constructeurs via Ergast API"""
    
    drivers_df = pd.DataFrame()
    constructors_df = pd.DataFrame()
    drivers_data = {}
    constructors_data = {}
    
    try:
        year = datetime.datetime.now().year
        schedule = fastf1.get_event_schedule(year)
        
        # Filtre des événements passés pour calculer les points
        now = datetime.datetime.now()
        completed_events = schedule[schedule['EventDate'] < now]

        for _, event in completed_events.iterrows():
            try:
                # Chargement des résultats de la course
                session = fastf1.get_session(year, event['RoundNumber'], 'R')
                session.load(telemetry=False, weather=False, messages=False)
                
                if hasattr(session, 'results'):
                    for _, row in session.results.iterrows():
                        abb = row['Abbreviation']
                        team = row['TeamName']
                        pts = row['Points']
                        
                        # Pilotes
                        if abb not in drivers_data:
                            drivers_data[abb] = {'Pilote': row['FullName'], 'Ecurie': team, 'Points': 0.0, 'Victoires': 0}
                        drivers_data[abb]['Points'] += pts
                        if row['Position'] == 1.0:
                            drivers_data[abb]['Victoires'] += 1
                            
                        # Constructeurs
                        if team not in constructors_data:
                            constructors_data[team] = {'Ecurie': team, 'Points': 0.0, 'Victoires': 0}
                        constructors_data[team]['Points'] += pts
                        if row['Position'] == 1.0:
                            constructors_data[team]['Victoires'] += 1
                
                # Gestion des points Sprint
                if event['EventFormat'] == 'sprint':
                    s_sess = fastf1.get_session(year, event['RoundNumber'], 'S')
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
            drivers_df = drivers_df.sort_values(by=['Points', 'Victoires'], ascending=False).reset_index(drop=True)
            drivers_df['Pos'] = drivers_df.index + 1
            drivers_df = drivers_df[['Pos', 'Pilote', 'Ecurie', 'Points', 'Victoires']]
            
        if constructors_data:
            constructors_df = pd.DataFrame(constructors_data.values())
            constructors_df = constructors_df.sort_values(by=['Points', 'Victoires'], ascending=False).reset_index(drop=True)
            constructors_df['Pos'] = constructors_df.index + 1
            constructors_df = constructors_df[['Pos', 'Ecurie', 'Points', 'Victoires']]
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération des classements : {e}")
        
    return drivers_df, constructors_df

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

# --- 3. LOGIQUE D'AFFICHAGE ---
def main():
    st.title("🏁 F1 Dashboard 2026")
    
    # Récupération des données
    now = datetime.now()
    actual_year = now.year
    actual_date = pd.to_datetime(now.strftime("%Y-%m-%d"))

    df_calendar = get_calendar(actual_year)
    
    next_index = (df_calendar['EventDate'] - actual_date).abs().idxmin()

    # On récupère la ligne complète
    next_event = df_calendar.loc[next_index]

    pays = next_event['Country']
    iso_code = DRAPEAUX.get(pays, "un")
    url_drapeau = f"https://flagcdn.com/w40/{iso_code}.png"
    
    if not next_event.empty:
        # Calcul du countdown
        delta = next_event['Session5DateUtc'] - actual_date
        jours = delta.days
        heures = delta.seconds // 3600
        nom_gp = next_event['EventName'].upper()
        pays_lieu = f"ROUND {next_event['RoundNumber']} • {next_event['Country']} • {next_event['Location']}"

        # Affichage du bloc principal
        st.markdown(f"""
            <div class="f1-container">
                <span class="f1-tag">Next Race</span>
                <div class="f1-title">{next_event['EventName'].upper()} <img src="{url_drapeau}" style="width:40px; margin-right:15px; vertical-align:middle;"> </div>
                <p style="font-size: 1.2em; color: #949498;">
                    ROUND {next_event['RoundNumber']} • {next_event['Country']} • {next_event['Location']}
                </p>
            </div>
        """, unsafe_allow_html=True)

        # On prépare la balise image ici pour ne pas encombrer le markdown
        img_html = f'<img src="{url_drapeau}" style="width:40px; margin-left:12px; vertical-align:middle; border-radius:2px;">'

        # --- Un seul markdown pour tout le bloc ---
        st.markdown(f"""
            <div class="f1-container">
                <span class="f1-tag">Next Race</span>
                
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px;">
                    <div class="f1-title" style="margin: 0; font-family: sans-serif; font-weight: bold; color: white; font-size: 2em; display: flex; align-items: center;">
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
                
                <div style="border-top: 1px solid #38383f; margin: 15px 0;"></div>
                
                <p style="color: #949498; margin: 0; font-family: sans-serif; font-size: 0.9em; letter-spacing: 0.5px;">
                    {pays_lieu}
                </p>
            </div>
        """, unsafe_allow_html=True)

        # Colonnes pour Tracé + Métriques
        col_img, col_metrics = st.columns([1, 1])

        with col_img:
            # URL dynamique vers le tracé (nomenclature officielle F1)
            circuit_id = next_event['Country'].replace(" ", "_")
            st.image(f"https://www.formula1.com/content/dam/fom-website/20px/circuits/{circuit_id}.png", 
                    caption=f"Tracé de {next_event['Location']}", 
                    use_column_width=True)

        with col_metrics:
            st.metric("Temps restant", f"{delta.days}j {delta.seconds // 3600}h")
            st.metric("Départ de la course", next_event['Session5DateUtc'].strftime("%H:%M"))
            st.write("---")
            with st.expander("📅 Horaires complets (H+1)"):
                st.write(f"**EL1:** {next_event['Session1DateUtc'].strftime('%d/%m à %H:%M')}")
                st.write(f"**Qualifs:** {next_event['Session4DateUtc'].strftime('%d/%m à %H:%M')}")
                st.write(f"**Course:** {next_event['Session5DateUtc'].strftime('%d/%m à %H:%M')}")
    else:
        st.info("La saison est terminée ! Rendez-vous l'année prochaine.")

    # Affichage du calendrier complet en dessous (optionnel)
    if st.checkbox("Voir tout le calendrier"):
        st.dataframe(df_calendar, use_container_width=True)

if __name__ == "__main__":
    main()

# --- CONFIGURATION DU STYLE F1 ---
st.markdown("""
    <style>
    /* Style pour le titre et les cartes */
    .f1-title {
        color: #FF1801; /* Le rouge officiel F1 */
        font-family: 'Arial Black', sans-serif;
        text-transform: uppercase;
        letter-spacing: 2px;
        border-bottom: 2px solid #FF1801;
    }
    .f1-card {
        background-color: #15151E; /* Le noir anthracite F1 */
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #FF1801;
        color: white;
        margin-bottom: 10px;
    }
    .f1-date {
        color: #949498;
        font-size: 0.9em;
    }
    </style>
    """, unsafe_allow_html=True)

def display_next_event(df_calendar):
    # 1. Récupérer la date actuelle (en string comme dans ton exemple précédent, ou datetime)
    # Si ton actual_date est un str : maintenant = pd.to_datetime(actual_date)
    maintenant = datetime.now() 

    # 2. Trouver le prochain événement (le plus proche dans le futur)
    futurs = df_calendar[df_calendar['Session5DateUtc'] >= maintenant]
    
    if futurs.empty:
        st.warning("Plus de courses prévues pour cette saison !")
        return

    prochain = futurs.iloc[0] # Le premier après maintenant
    
    # 3. Calcul du compte à rebours (Countdown)
    delta = prochain['Session5DateUtc'] - maintenant
    jours = delta.days
    heures = delta.seconds // 3600

    # --- AFFICHAGE STREAMLIT ---
    st.markdown('<h1 class="f1-title">NEXT GRAND PRIX</h1>', unsafe_allow_html=True)
    
    # Carte principale
    with st.container():
        st.markdown(f"""
            <div class="f1-card">
                <p class="f1-date">ROUND {prochain['RoundNumber']} • {prochain['Country'].upper()}</p>
                <h2 style="margin:0; color:white;">{prochain['EventName']}</h2>
                <p style="margin:5px 0;">📍 {prochain['Location']}</p>
            </div>
        """, unsafe_allow_html=True)

    # Métriques (Countdown)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("JOURS", jours)
    with col2:
        st.metric("HEURES", heures)
    with col3:
        # Affichage de l'heure de la course (Session 5)
        heure_course = prochain['Session5DateUtc'].strftime("%H:%M")
        st.metric("DÉPART (H+1)", heure_course)

    # Optionnel : Détail des sessions si tu les as dans ton DF
    with st.expander("Voir le programme complet"):
        st.write(f"**Essais Libres 1 :** {prochain['Session1DateUtc'].strftime('%d %b %H:%M')}")
        st.write(f"**Qualifications :** {prochain['Session4DateUtc'].strftime('%d %b %H:%M')}")
        st.write(f"**Grand Prix :** {prochain['Session5DateUtc'].strftime('%d %b %H:%M')}")


display_next_event(df_calendar)
