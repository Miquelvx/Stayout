import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import GradientBoostingRegressor

from fonctions_predictions import initialize_feature_df, save_to_master_db, encoding_label

db_path = './Database/f1_2026_master_db.csv'

def calculate_podium_proba(pos):
    # Formule mathématique pour convertir la position en probabilité (0 à 100)
    # On centre la chute de probabilité autour de la 3.5ème place
    proba = 1 / (1 + np.exp((pos - 3.5) * 2))
    return round(proba * 100, 1)

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

# 2. Initialiser les données fraîches du GP2 (Qualifs terminées)
df_next_gp = initialize_feature_df(2026, 2)

# 3. Récupérer le momentum (last_qualif_pos) du GP précédent
mapping_last_quali = df_master[df_master['RoundNumber'] == 1].set_index('Abbreviation')['qualif_pos'].to_dict()
df_next_gp['last_qualif_pos'] = df_next_gp['Abbreviation'].map(mapping_last_quali)

#save_to_master_db(df_next_gp, db_path)

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
# n_estimators=100 : 100 arbres de décision vont voter pour le résultat
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

print("--- PRÉDICTION ---")
print(results[['Driver', 'predicted_pos', 'Podium_Proba_pct']])

# Récupération des importances
importances = model.feature_importances_
indices = np.argsort(importances)

plt.figure(figsize=(10, 6))
plt.title('Quels facteurs ont décidé de ce classement ?')
plt.barh(range(len(indices)), importances[indices], color='skyblue', align='center')
plt.yticks(range(len(indices)), [features[i] for i in indices])
plt.xlabel('Importance Relative')
plt.show()