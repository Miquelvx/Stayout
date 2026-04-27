# Stayout

Stayout est une application Streamlit qui exploite les données de la saison de Formule 1 2026 pour analyser les performances et prédire les résultats de chaque Grand Prix grâce à un modèle de Machine Learning.

## Fonctionnalités
- Données temps réel via FastF1 API (télémétrie, vitesse, DRS, freinage)
- Prédictions ML (Gradient Boosting) entraîné sur l'historique de la saison
- Rapports PDF générés automatiquement avant et après chaque course
- Conservation des données via Google Sheets API (sans fichiers locaux)
- Visualisations interactives avec Plotly

## Hébergement Cloud
Déploiment via Streamlit.

## Stack Technique

| Catégorie | Technologies |
|---|---|
| App & UI | Streamlit · Plotly |
| Machine Learning | scikit-learn · Pandas · NumPy |
| Données F1 | FastF1 · OpenWeatherMap API |
| Stockage | Google Sheets API · gspread |
| PDF | ReportLab · Matplotlib |

## Structure du projet

```bash
Stayout/                                    # Répertoire du projet Stayout
├── .streamlit/                             # Répertoire pour la configuration de Streamlit
├── Code/                                   # Répertoire contenant le code du projet
├── _pycache_/                              # Répertoire des fichiers pour le cache des scripts python
├── assets/                                 # Répertoire des fichiers images du projet
├── pages/                                  # Répertoire des fichiers des pages Streamlit
├── .gitattributes                          # Fichier .gitattributes du projet
├── .gitignore                              # Fichier .gitignore du projet
├── Accueil_🏠.py                           # Fichier python de la page d'accueil
├── README.md                               # Fichier README du projet
└── requirements.tx                         # Fichier contenant les dépendances à installer
```

```bash
Code/                                       # Répertoire contenant le code du projet
├── _pycache_/                              # Répertoire des fichiers pour le cache des scripts python
│   ├── ...                                 # Contient les fichiers .pyc pour les bytecode du module python 
├── script_test                             # Répertoire des notebooks de test
├── constants.py                            # Fichier pythoncontenant les constantes du projet 
├── fonctions_cache_data.py                 # Fichier python contenant les fonctions pour le cache des données
├── fonctions_create_plot.py                # Fichier python contenant les fonctions pour la création des graphiques
├── fonctions_generate_pdf.py               # Fichier python contenant les fonctions pour la génération des rapports PDF
├── fonctions_get_data.py                   # Fichier python contenant les fonctions pour la récupération des données
├── fonctions_google_sheet.py               # Fichier python contenant les fonctions pour le stockage des données sur Google Sheets
└── fonctions_predictions.py                # Fichier python contenant les fonctions pour les prédictions
```

```bash
pages/                                      # Répertoire des fichiers des pages Streamlit
├── Analyse_de_course_🏁.py                 # Fichier python de la page d'analyse de course
├── Head_to_head_qualification_⚔️.py        # Fichier python de la page head to head des télémétries de qualification
├── Prédiction_de_course_⚙️.py              # Fichier python de la page de prédiction de course
└── Replay_de_course_📹.py                  # Fichier python de la page de replay de course (Not Finished)
```

## Auteurs

© 2026 / Mike Leveleux

