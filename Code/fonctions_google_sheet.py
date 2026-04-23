### ======== STAYOUT - Fonctions Google Sheets ======== ### 

# ----------------------------
# IMPORTATIONS DES LIBRAIRIES
# ----------------------------
import gspread
import pandas as pd
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import streamlit as st

# Connexion google sheets
def get_gspread_client():
    credentials = st.secrets["gcp_service_account"]
    client = gspread.service_account_from_dict(credentials)
    return client

# Lecture google sheets
def read_sheet(spreadsheet_name, worksheet_name):
    client = get_gspread_client()
    spreadsheet = client.open(spreadsheet_name)
    worksheet = spreadsheet.worksheet(worksheet_name)
    df = get_as_dataframe(worksheet, evaluate_formulas=True).dropna(how="all")
    return df

# Écriture google sheets
def write_sheet(spreadsheet_name, worksheet_name, df):
    client = get_gspread_client()
    spreadsheet = client.open(spreadsheet_name)
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=50)
    set_with_dataframe(worksheet, df)

# Vérification google sheets
def sheet_exists(spreadsheet_name, worksheet_name):
    client = get_gspread_client()
    try:
        spreadsheet = client.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        return len(worksheet.get_all_values()) > 1
    except (gspread.exceptions.WorksheetNotFound, gspread.exceptions.SpreadsheetNotFound):
        return False

# Master DB
def save_to_master_db_sheet(df_new, spreadsheet_name="f1_2026_master_db", worksheet_name="f1_2026_master_db"):
    current_round = df_new['RoundNumber'].iloc[0]
    current_year = df_new['Year'].iloc[0]
    if sheet_exists(spreadsheet_name, worksheet_name):
        df_old = read_sheet(spreadsheet_name, worksheet_name)
        is_already_present = ((df_old['RoundNumber'] == current_round) & (df_old['Year'] == current_year)).any()
        if is_already_present:
            print(f"ℹ️ GP {current_round} ({current_year}) déjà présent. Pas d'ajout.")
            return
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_combined = df_new
    write_sheet(spreadsheet_name, worksheet_name, df_combined)
    print(f"✅ GP {current_round} ({current_year}) ajouté dans Google Sheets.")

# Sauvegarde prédiction DB
def save_prediction_sheet(results, round_num, year, spreadsheet_name="Predictions_2026"):
    worksheet_name = f"prediction_R{round_num}_{year}"
    write_sheet(spreadsheet_name, worksheet_name, results.reset_index())
    print(f"✅ Prédiction R{round_num}_{year} sauvegardée.")

# Lecture prédiction DB
def read_prediction_sheet(round_num, year, spreadsheet_name="Predictions_2026"):
    worksheet_name = f"prediction_R{round_num}_{year}"
    return read_sheet(spreadsheet_name, worksheet_name)

# Vérification prédiction DB
def prediction_exists(round_num, year, spreadsheet_name="Predictions_2026"):
    worksheet_name = f"prediction_R{round_num}_{year}"
    return sheet_exists(spreadsheet_name, worksheet_name)

# Accuracy log DB
def log_accuracy_sheet(round_num, mae_rank, mae_raw, top1_check, spreadsheet_name="Accuracy_log"):
    worksheet_name = "Accuracy_log"
    new_row = pd.DataFrame([{
        'RoundNumber': round_num,
        'MAE_Rank': round(mae_rank, 2),
        'MAE_Raw': round(mae_raw, 2),
        'Win_Prediction': top1_check
    }])
    if sheet_exists(spreadsheet_name, worksheet_name):
        df_log = read_sheet(spreadsheet_name, worksheet_name)
        if (df_log['RoundNumber'] == round_num).any():
            print(f"⚠️ Stats du Round {round_num} déjà présentes.")
            return
        df_log = pd.concat([df_log, new_row], ignore_index=True)
    else:
        df_log = new_row
    write_sheet(spreadsheet_name, worksheet_name, df_log)
    print(f"✅ Accuracy Round {round_num} loggée.")

# Sauvegarde feature importantes DB
def save_importance_sheet(df_importance, round_num, year, spreadsheet_name="Feature_Importante"):
    worksheet_name = f"importance_R{round_num}_{year}"
    write_sheet(spreadsheet_name, worksheet_name, df_importance)
    print(f"✅ Feature importance R{round_num}_{year} sauvegardée.")

# Lecture feature importantes DB
def read_importance_sheet(round_num, year, spreadsheet_name="Feature_Importante"):
    worksheet_name = f"importance_R{round_num}_{year}"
    return read_sheet(spreadsheet_name, worksheet_name)

# Vérification feature importantes DB
def importance_exists(round_num, year, spreadsheet_name="Feature_Importante"):
    worksheet_name = f"importance_R{round_num}_{year}"
    return sheet_exists(spreadsheet_name, worksheet_name)