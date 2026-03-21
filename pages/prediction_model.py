import os
import pandas as pd
import numpy as np
import streamlit as st

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

from Code.fonctions_predictions import initialize_feature_df, calculate_podium_proba, save_to_master_db, encoding_label

# ----------------------------
# CONFIG
# ----------------------------

st.set_page_config(page_title="StayOut - Race Analysis", layout="wide")

if 'actual_year' in st.session_state:
    actual_year = st.session_state['actual_year']

if 'df_calendar{actual_year}' in st.session_state:
    df_calendar = st.session_state['df_calendar{actual_year}']


def main():

    st.title("Prediction GP")

    db_path = './Database/f1_2026_master_db.csv'

    # Sécurité dossier Database
    if not os.path.exists('./Database'):
        os.makedirs('./Database')

    # Sécurité dossier Predictions
    if not os.path.exists('./Database/Predictions'):
        os.makedirs('./Database/Predictions')

    if not os.path.exists(db_path):
        # Initialisation données premier GP
        print(" Première initialisation : Création du Master DB...")
        df_master = initialize_feature_df(2026, 1)

        # Sauvegarde dataframe dans CSV
        save_to_master_db(df_master, db_path)
    else : 
        # Lecture CSV données origine
        print(" Database trouvée. Chargement de l'historique...")
        df_master = pd.read_csv(db_path)

    actual_date =  pd.to_datetime("2026-03-20, 12:00:00")
    futur_events = df_calendar[df_calendar['Session5DateUtc'] > actual_date]
    past_events = df_calendar[df_calendar['Session5DateUtc'] < actual_date]

    if not futur_events.empty:
        next_index = futur_events['Session5DateUtc'].idxmin()
        next_event = df_calendar.loc[next_index]

        last_index = past_events['Session5DateUtc'].idxmax()
        last_event = df_calendar.loc[last_index]

        if actual_date > last_event['Session5DateUtc'] and last_event['RoundNumber'] != 1 and df_master['RoundNumber'].max() != last_event['RoundNumber']:
            
            # 2. Initialiser les données du GP passé
            df_last_gp = initialize_feature_df(2026, last_event['RoundNumber'])

            # 3. Récupérer le momentum (last_qualif_pos) du GP précédent
            mapping_last_quali = df_master[df_master['RoundNumber'] == last_event['RoundNumber']-1].set_index('Abbreviation')['qualif_pos'].to_dict()
            df_last_gp['last_qualif_pos'] = df_last_gp['Abbreviation'].map(mapping_last_quali)

            save_to_master_db(df_last_gp, db_path)

        elif next_event['Session4DateUtc'] < actual_date < next_event['Session5DateUtc']:
            # 2. Initialiser les données du GP actuel pour la prédiction
            df_next_gp = initialize_feature_df(2026, next_event['RoundNumber'])

            # 3. Récupérer le momentum (last_qualif_pos) du GP précédent
            mapping_last_quali = df_master[df_master['RoundNumber'] == next_event['RoundNumber']-1].set_index('Abbreviation')['qualif_pos'].to_dict()
            df_next_gp['last_qualif_pos'] = df_next_gp['Abbreviation'].map(mapping_last_quali)

            df_master, df_next_gp, encoders = encoding_label(df_master, df_next_gp)

            features = [
                'Abbreviation', 'TeamName', 'qualif_pos', 'last_qualif_pos', 
                'GapFromPole_pct', 'is_incident_quali', 'topspeed_kmh_qualif', 
                'constructor_pos', 'team_performance_lastgp', 
                'air_temp_forecast', 'track_temp_forecast', 'rain_proba_forecast'
            ]

            # On entraîne sur l'historique (en filtrant les abandons techniques pour plus de pureté)
            train_set = df_master[df_master['is_race_incident'] == 0]

            X_train = train_set[features].copy()
            y_train = train_set['race_finish_pos'].copy()

            X_predict = df_next_gp[features].copy()

            # Création du modèle
            model = GradientBoostingRegressor(
                n_estimators=100, 
                learning_rate=0.1, 
                max_depth=3, 
                random_state=42
            )

            # Entraînement
            model.fit(X_train, y_train)

            # Prédiction
            predictions = model.predict(X_predict)

            # On ajoute les prédictions au DataFrame pour plus de clarté
            df_next_gp['predicted_pos'] = predictions

            # On trie pour voir qui finit premier selon l'IA
            results = df_next_gp[['Abbreviation', 'predicted_pos']].sort_values(by='predicted_pos')

            # Appliquer la fonction à ton DataFrame de résultats
            results['Podium_Proba_pct'] = results['predicted_pos'].apply(calculate_podium_proba)

            # --- ÉTAPE FINALE : Traduction pour l'humain ---
            # On utilise l'encodeur stocké précédemment pour retrouver le nom du pilote
            results['Driver'] = encoders['Abbreviation'].inverse_transform(results['Abbreviation'])
            results['RoundNumber'] = df_next_gp['RoundNumber'].iloc[0]
            results = results.sort_values(by='predicted_pos')

            # 2. Reset l'index
            # drop=True : supprime l'ancien index au lieu de le garder comme colonne
            results = results.reset_index(drop=True)

            # 3. Décaler l'index de +1 pour commencer à 1 au lieu de 0
            results.index = results.index + 1

            # Optionnel : Renommer l'index pour qu'il s'affiche comme "Pos"
            results.index.name = 'Pos'

            round_num = df_next_gp['RoundNumber'].iloc[0]
            year = df_next_gp['Year'].iloc[0]
            filename = f"./Database/Predictions/prediction_R{round_num}_{year}.csv"

            results.to_csv(filename, index_label='Predicted_Rank')

            st.text(f"Voici les prédictions pour le {next_event['EventName']}")
            st.dataframe(results[['Driver', 'predicted_pos', 'Podium_Proba_pct']])

            # Récupération des importances
            importances = model.feature_importances_
            indices = np.argsort(importances)

            top_indices = indices[::-1]

            print("--- Importance des variables ---")
            for i in top_indices:
                print(f"{features[i]:<30} : {importances[i]:.4f}")

            """
            plt.figure(figsize=(10, 6))
            plt.title('Quels facteurs ont décidé de ce classement ?')
            plt.barh(range(len(indices)), importances[indices], color='skyblue', align='center')
            plt.yticks(range(len(indices)), [features[i] for i in indices])
            plt.xlabel('Importance Relative')
            plt.show()"""

        elif actual_date < next_event['Session4DateUtc']:
            print(f"Les qualification du {next_event['EventName']} ne sont pas encore passées.")
            st.info(f"Les qualification du {next_event['EventName']} ne sont pas encore passées.")

            # 1. PRÉPARATION DES DONNÉES DE COMPARAISON 
            last_round = next_event['RoundNumber'] - 1
            df_last_prediction = pd.read_csv(f"./Database/Predictions/prediction_R{last_round}_{2026}.csv")

            # Récupération des vrais résultats dans le Master
            df_actual = df_master[df_master['RoundNumber'] == last_round][['Abbreviation', 'race_finish_pos']]

            df_compare = pd.merge(df_last_prediction, df_actual, left_on='Driver', right_on='Abbreviation')

            # --- 2. CALCUL DES DEUX MÉTRIQUES ---
            # MAE sur le rang final -> Performance "Sportive"
            mae_rank = mean_absolute_error(df_compare['race_finish_pos'], df_compare['Predicted_Rank'])

            # MAE sur la valeur brute -> Précision du "Cerveau"
            mae_raw = mean_absolute_error(df_compare['race_finish_pos'], df_compare['predicted_pos'])

            # --- 3. SÉCURITÉ ET ENREGISTREMENT DANS LE LOG ---
            log_file = './Database/Predictions/accuracy_log.txt'
            top1_check = df_compare.iloc[0]['race_finish_pos'] == 1.0
            log_entry = f"Round {last_round} | MAE_Rank: {mae_rank:.2f} | MAE_Raw: {mae_raw:.2f} | Win_Prediction: {top1_check}\n"

            already_logged = False
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    if f"Round {last_round} |" in f.read():
                        already_logged = True

            if not already_logged:
                with open(log_file, 'a') as f:
                    f.write(log_entry)
                print(f"✅ Analyse Round {last_round} terminée.")
                print(f"   -> Erreur Rank (Places) : {mae_rank:.2f}")
                print(f"   -> Erreur Raw (Maths)   : {mae_raw:.2f}")
            else:
                print(f"⚠️ Stats du Round {last_round} déjà présentes. Log ignoré.")

            # Affichage rapide du top 5 pour vérification visuelle
            st.text(f"Résultat et prédiction du Round {last_round}")
            st.dataframe(df_compare[['Driver', 'Predicted_Rank', 'race_finish_pos']])

            st.text("Mean absolute error model :")
            st.text(f"MAE Rank : {mae_rank:.2f}")
            st.text(f"MAE Raw : {mae_raw:.2f}")
    else:
        st.info("La saison est terminée, rendez-vous l'année prochaine.")

if __name__ == "__main__":
    main()
