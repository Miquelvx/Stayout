### ======== STAYOUT - Prediction ======== ### 

# ----------------------------
# IMPORTATIONS DES LIBRAIRIES
# ----------------------------
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

from Code.fonctions_predictions import initialize_feature_df_race, initialize_feature_df_qualif, calculate_podium_proba, encoding_label
from Code.fonctions_google_sheet import sheet_exists, read_sheet, save_to_master_db_sheet, save_prediction_sheet, read_prediction_sheet, prediction_exists, save_importance_sheet, read_importance_sheet, importance_exists, log_accuracy_sheet
from Code.fonctions_generate_pdf import generate_comparison_pdf, generate_prediction_pdf

# ----------------------------
# CONFIG
# ----------------------------

st.set_page_config(page_title="Stayout - Prédiction de course", layout="wide")

if 'actual_date' in st.session_state:
    actual_date = st.session_state['actual_date']
    #actual_date = pd.to_datetime("2026-03-28 12:00:00")

if 'actual_year' in st.session_state:
    actual_year = st.session_state['actual_year']

if 'df_calendar{actual_year}' in st.session_state:
    df_calendar = st.session_state['df_calendar{actual_year}']

if 'delta' in st.session_state:
    delta = st.session_state['delta']
    jours = delta.days
    heures = delta.seconds // 3600

if 'constructors_df' in st.session_state:
    constructors_df = st.session_state['constructors_df']

# CSS Affichage tableau prédictions
st.markdown("""
            <style>
                .f1-table {
                    width: 40%;
                    border-collapse: collapse;
                    font-family: 'Titillium Web', sans-serif;
                    background-color: #15151e;
                    color: white;
                    border: 5px solid;
                    border-radius: 10px;
                    overflow: hidden;
                    text-align: center;
                    margin: 0 auto;
                }
                .f1-row {
                    border-bottom: 1px solid #38383f;
                    transition: background 0.3s;
                }
                .f1-row:hover {
                    background-color: #1f1f27;
                }
                .f1-header {
                    background-color: #e10600;
                    color: white;
                    text-transform: uppercase;
                    font-weight: bold;
                    font-size: 1em;
                    padding: 5px;
                    text-align: center;
                }
                .driver-cell {
                    padding: 12px;
                    font-weight: bold;
                    font-size: 0.8em;
                }
                .pos-cell {
                    text-align: center;
                    width: 60px;
                    font-weight: 600;
                    background: rgba(255,255,255,0.05);
                }
                .diff-badge {
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.8em;
                    font-weight: bold;
                }
                .diff-up { background-color: #09ab3b; color: black; }
                .diff-down { background-color: #aa0909; color: white; }
                .diff-equal { background-color: #38383f; color: white; }
            </style>
            """, unsafe_allow_html=True)

# ----------------------------
# MAIN STREAMLIT APP
# ----------------------------
def main():

    st.title("🏁 Prédiction des résultat de Grand Prix 🏁")

    st.markdown(""" *Objectif : Exploiter les données de la nouvelle réglementation F1 2026 pour anticiper la hiérarchie des Grands Prix.* """)

    # --- SOURCES ---
    col_a, col_b = st.columns(2)
    with col_a:
        st.caption("📂 **Données F1 :** FastF1 API")
    with col_b:
        st.caption("☁️ **Météo :** OpenWeatherMap API")

    # --- DICTIONNAIRE DES DONNÉES ---
    with st.expander("📊 Architecture des Données"):

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("##### 🏎️ Performance Pilote")
            st.markdown("""
            - **`Abbreviation`** : Identifiant unique (ex: LEC, VER).
            - **`qualif_pos`** : Position sur la grille de départ.
            - **`qualif_time`** : Meilleur chrono (en secondes).
            - **`GapFromPole_pct`** : Écart relatif à la pole position (%).
            - **`topspeed_kmh_qualif`** : Vitesse de pointe enregistrée.
            - **`is_incident_quali`** : Incident en qualif (0/1).
            """)

            st.markdown("##### 🛠️ Data Écurie")
            st.markdown("""
            - **`TeamName`** : Nom de l'écurie.
            - **`constructor_pos`** : Classement mondial avant la course.
            - **`team_performance_lastgp`** : Points marqués au GP précédent.
            """)

        with col2:
            st.markdown("##### 🏁 Historique & Course")
            st.markdown("""
            - **`race_finish_pos`** : **Variable cible (Position finale).**
            - **`last_qualif_pos`** : Position de départ au dernier GP.
            - **`is_race_incident`** : Abandon ou problème technique (0/1).
            - **`RoundNumber`** : Numéro de l'épreuve dans la saison.
            """)

            st.markdown("##### 🌡️ Environnement (Forecast)")
            st.markdown("""
            - **`air_temp_forecast`** : Température de l'air attendue.
            - **`track_temp_forecast`** : Température de la piste estimée.
            - **`rain_proba_forecast`** : Probabilité de précipitations.
            """)

    # --- FOCUS TECHNIQUE ---
    st.markdown("""
        <div style="background-color: transparent; border: 1px solid #4b4b4b; padding: 10px; border-radius: 5px; font-size: 1em;">
            Le <strong>GapFromPole_pct</strong> est crucial : chaque circuit ayant une longueur différente, un écart de 1 seconde à Spa n'a pas la même valeur qu'à Monaco. Le pourcentage permet de normaliser cette performance sur toute la saison.
        </div>
    """, unsafe_allow_html=True)

    # --- SECURITE GOOGLE SHEETS ---
    if sheet_exists("f1_2026_master_db", "f1_2026_master_db"):
        df_master = read_sheet("f1_2026_master_db", "f1_2026_master_db")
    else:
        df_master = initialize_feature_df_race(2026, 1)
        save_to_master_db_sheet(df_master)

    futur_events = df_calendar[df_calendar['Session5DateUtc'] >= actual_date]
    past_events = df_calendar[df_calendar['Session5DateUtc'] < actual_date]

    if not futur_events.empty:
        next_index = futur_events['Session5DateUtc'].idxmin()
        next_event = df_calendar.loc[next_index]

        last_index = past_events['Session5DateUtc'].idxmax()
        last_event = df_calendar.loc[last_index]

        # Cas 1 : Date situé entre les qualifications et le grand prix -> Prédiction de la course
        if next_event['Session4DateUtc'] < actual_date < next_event['Session5DateUtc']:
            st.markdown("---")
            # Compte à rebours départ course
            st.markdown(f"""
                <div style="background-color: #15151e; border-left: 5px solid #e10600; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <span style="color: white; text-transform: uppercase; font-size: 1em; font-weight: 900; font-family: 'Titillium Web', sans-serif;">
                        Départ de la course dans {heures}H <span style="color: #e10600;">•</span> {next_event['EventName'].upper()} 🏎️
                    </span>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("---")

            if not prediction_exists(next_event['RoundNumber'], 2026):
                # --- 1. Initialiser les données du GP actuel pour la prédiction ---
                df_next_gp = initialize_feature_df_qualif(2026, next_event['RoundNumber'])

                # --- 2. Récupérer le momentum (last_qualif_pos) du GP précédent ---
                mapping_last_quali = df_master[df_master['RoundNumber'] == next_event['RoundNumber']-1].set_index('Abbreviation')['qualif_pos'].to_dict()
                df_next_gp['last_qualif_pos'] = df_next_gp['Abbreviation'].map(mapping_last_quali)

                # --- 3. Encodage des données textuelles ---
                df_master, df_next_gp, encoders = encoding_label(df_master, df_next_gp)

                # Données retenues pour l'entrainement du modèle
                features = [
                    'Abbreviation', 'TeamName', 'qualif_pos', 'last_qualif_pos', 
                    'GapFromPole_pct', 'is_incident_quali', 'topspeed_kmh_qualif', 
                    'constructor_pos', 'team_performance_lastgp', 
                    'air_temp_forecast', 'track_temp_forecast', 'rain_proba_forecast'
                ]

                # On entraîne sur l'historique (en filtrant les abandons techniques)
                train_set = df_master[df_master['is_race_incident'] == 0]

                X_train = train_set[features].copy()
                y_train = train_set['race_finish_pos'].copy()

                X_predict = df_next_gp[features].copy()

                # --- 4. Création du modèle ---
                model = GradientBoostingRegressor(
                    n_estimators=100, 
                    learning_rate=0.1, 
                    max_depth=3, 
                    random_state=42
                )

                # --- 5. Entraînement ---
                model.fit(X_train, y_train)

                # --- 6. Prédiction ---
                predictions = model.predict(X_predict)

                # On ajoute les prédictions au DataFrame
                df_next_gp['predicted_pos'] = predictions

                # On trie pour voir qui finit premier
                results = df_next_gp[['Abbreviation', 'predicted_pos']].sort_values(by='predicted_pos')

                # Calcul de la probabilité de podium
                results['Podium_Proba_pct'] = results['predicted_pos'].apply(calculate_podium_proba)

                # --- 7. Traduction ---
                # On utilise l'encodeur stocké précédemment pour retrouver le nom du pilote
                results['Driver'] = encoders['Abbreviation'].inverse_transform(results['Abbreviation'])
                results['RoundNumber'] = df_next_gp['RoundNumber'].iloc[0]
                results = results.merge( df_next_gp[['Abbreviation', 'qualif_pos']],  left_on='Abbreviation',  right_on='Abbreviation',  how='left').drop(columns=['Abbreviation'])
                results = results.sort_values(by='predicted_pos')

                # --- 8. Nettoyage final ---
                results = results.reset_index(drop=True)
                results.index = results.index + 1
                results.index.name = 'Predicted_Rank'

                round_num = df_next_gp['RoundNumber'].iloc[0]
                year = df_next_gp['Year'].iloc[0]

                # --- 9. Sauvegarde dataframe en CSV ---
                save_prediction_sheet(results, round_num, year)

                # Récupération des données importantes
                importances = model.feature_importances_
                indices = np.argsort(importances)

                df_importance = pd.DataFrame({
                    'Feature': [features[i] for i in indices],
                    'Importance': importances[indices]
                })
                save_importance_sheet(df_importance, round_num, year)
            else: 
                results = read_prediction_sheet(next_event['RoundNumber'], 2026)
                df_importance = read_importance_sheet(next_event['RoundNumber'], 2026)

            # HTML Affichage Tableau
            html_table = '<table class="f1-table">'
            html_table += '''
                <thead>
                    <tr>   
                        <th class="f1-header">Pilote</th>
                        <th class="f1-header">Position Départ</th>
                        <th class="f1-header">Prédiction</th>
                        <th class="f1-header">Probabilité Podium</th>
                    </tr>
                </thead>
                <tbody>
            '''
            # Affichage ligne par ligne
            for index, row in results.iterrows():
                html_table += f'''<tr class="f1-row">
                                    <td class="driver-cell">{row['Driver']}</td>
                                    <td style="text-align:center">{int(row['qualif_pos'])}</td>
                                    <td style="text-align:center">{index+1}</td>
                                    <td style="text-align:center">{int(row['Podium_Proba_pct'])} %</td>
                                </tr>'''
            html_table += '</tbody></table>'

            # Titre
            st.markdown(f"""
                    <span style="color: white; font-size: 1.4em; font-weight: 900; letter-spacing: 1.5px; text-transform: uppercase; font-family: 'Titillium Web', sans-serif;">
                        🏁 PRÉDICTIONS DE COURSE <span style="font-weight: 300; opacity: 0.8;"></span>
                    </span> """, unsafe_allow_html=True)
            
            # Affichage du tableau final
            st.markdown(html_table, unsafe_allow_html=True)

            # Graphique plotly pour affichage
            fig = px.bar(
                df_importance, 
                x='Importance', 
                y='Feature', 
                orientation='h',
                title='⚙️ FACTEURS DÉCISIFS DU MODÈLE ⚙️',
                labels={'Importance': 'Poids dans la décision', 'Feature': 'Variable'},
                color='Importance',
                color_continuous_scale='Reds'
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color="white",
                title_font_size=20,
                xaxis=dict(showgrid=True, gridcolor='#38383f'),
                yaxis=dict(showgrid=False),
                showlegend=False,
                height=500
            )
            st.markdown("---")
            st.plotly_chart(fig, use_container_width=True)

            # Génération rapport PDF
            st.markdown("---")
            pdf_buffer = generate_prediction_pdf(
                results = results,
                df_importance = df_importance,
                event_name = next_event['EventName'],
                round_num = int(next_event['RoundNumber']),
                date_event = next_event['EventDate'],
                year = actual_year
            )
            st.download_button(
                label="📄 Télécharger le rapport de prédiction",
                data=pdf_buffer,
                file_name=f"StayOut_Prediction_PRE_R{int(next_event['RoundNumber'])}_2026.pdf",
                mime="application/pdf",
                use_container_width=True
            )       

        # Cas 2 : Date après le Grand Prix -> récupération des résultats et comparaison
        elif actual_date < next_event['Session4DateUtc']:
            
            if df_master['RoundNumber'].max() != last_event['RoundNumber']:
                # 1. Initialiser les données du GP passé
                df_last_gp = initialize_feature_df_race(2026, last_event['RoundNumber'])

                # 2. Récupérer le momentum (last_qualif_pos) du GP précédent
                mapping_last_quali = df_master[df_master['RoundNumber'] == last_event['RoundNumber']-1].set_index('Abbreviation')['qualif_pos'].to_dict()
                df_last_gp['last_qualif_pos'] = df_last_gp['Abbreviation'].map(mapping_last_quali)

                save_to_master_db_sheet(df_last_gp)

            st.markdown("---")
            # Compte à rebours next GP
            st.markdown(f"""
                <div style="background-color: #15151e; border-left: 5px solid #e10600; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <span style="color: #888; text-transform: uppercase; font-size: 0.8em; font-weight: bold; letter-spacing: 1px;">Prochain Départ</span><br>
                    <span style="color: white; font-size: 1.5em; font-weight: 900; font-family: 'Titillium Web', sans-serif;">
                        🏎️ {jours}J {heures}H <span style="color: #e10600;">•</span> {next_event['EventName'].upper()}
                    </span>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader(f"Prédictions du modèle pour le {last_event['EventName']}")
            st.caption(f"✨ Modèle entraîné sur l'historique 2026")

            print(f"Les qualification du {next_event['EventName']} ne sont pas encore passées.")

            # --- 3. Préparation des données de comparaison ---
            df_master = read_sheet("f1_2026_master_db", "f1_2026_master_db")
            last_round = next_event['RoundNumber'] - 1
            df_last_prediction = read_prediction_sheet(last_round, 2026)

            # Récupération des vrais résultats dans le Master
            df_actual = df_master[df_master['RoundNumber'] == last_round][['Abbreviation', 'race_finish_pos']]

            df_compare = pd.merge(df_last_prediction, df_actual, left_on='Driver', right_on='Abbreviation')
            df_compare = df_compare.sort_values(by='race_finish_pos').reset_index(drop=True)

            # --- 4. Calcul des deux métriques ---
            # MAE sur le rang final -> Performance "Sportive"
            mae_rank = mean_absolute_error(df_compare['race_finish_pos'], df_compare['Predicted_Rank'])

            # MAE sur la valeur brute -> Précision du "Cerveau"
            mae_raw = mean_absolute_error(df_compare['race_finish_pos'], df_compare['predicted_pos'])

            # --- 5. Sécurité et enregistrement dans le log ---
            top1_check = df_compare.iloc[0]['Predicted_Rank'] == 1.0

            log_accuracy_sheet(last_round, mae_rank, mae_raw, top1_check)

            # --- 6. Affichage des résultats ---
            # Affichage des métriques MAE
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(label="🎯 MAE Rank", value=f"{mae_rank:.2f}", delta_color="inverse")
                st.caption("Erreur moyenne en positions")

            with col2:
                st.metric(label="🧮 MAE Raw", value=f"{mae_raw:.2f}", delta_color="inverse")
                st.caption("Précision brute du modèle")

            with col3:
                status_win = "✅ RÉUSSIE" if top1_check else "❌ ÉCHOUÉE"
                st.metric(label="🏆 Prediction Vainqueur", value=status_win)

            st.markdown("---")

            st.subheader(f"🏁 Prédiction VS Réalité : {last_event['EventName']}")

            # HTML Affichage Tableau
            html_table = '<table class="f1-table">'
            html_table += '''
                <thead>
                    <tr>   
                        <th class="f1-header" style="width:50px">Pos</th>
                        <th class="f1-header">Pilote</th>
                        <th class="f1-header">Prédiction</th>
                        <th class="f1-header">Réel</th>
                        <th class="f1-header">Écart</th>
                    </tr>
                </thead>
                <tbody>
            '''
            # Affichage ligne par ligne
            for _, row in df_compare.iterrows():
                diff = int(row['race_finish_pos'] - row['Predicted_Rank'])
                if diff == 0:
                    badge = '<span class="diff-badge diff-equal">0</span>'
                elif diff > 0:
                    badge = f'<span class="diff-badge diff-down">+{diff}</span>'
                else:
                    badge = f'<span class="diff-badge diff-up">{diff}</span>'
                html_table += f'''<tr class="f1-row">
                                    <td class="pos-cell">{int(row['race_finish_pos'])}</td>
                                    <td class="driver-cell">{row['Driver']}</td>
                                    <td style="text-align:center">{int(row['Predicted_Rank'])}</td>
                                    <td style="text-align:center">{int(row['race_finish_pos'])}</td>
                                    <td style="text-align:center">{badge}</td>
                                </tr>'''
            html_table += '</tbody></table>'

            # Affichage du tableau final
            st.markdown(html_table, unsafe_allow_html=True)

            # Génération rapport PDF
            st.markdown("---")
            pdf_buffer = generate_comparison_pdf(
                df_compare = df_compare,
                mae_rank = mae_rank,
                mae_raw = mae_raw,
                top1_check = top1_check,
                event_name = last_event['EventName'],
                round_num = int(last_event['RoundNumber']),
                date_event = last_event['EventDate'],
                year = actual_year
            )
            st.download_button(
                label="📄 Télécharger l'analyse post-course",
                data=pdf_buffer,
                file_name=f"StayOut_Analysis_POST_R{int(last_event['RoundNumber'])}_2026.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    else:
        st.info("La saison est terminée, rendez-vous l'année prochaine.")

if __name__ == "__main__":
    main()
