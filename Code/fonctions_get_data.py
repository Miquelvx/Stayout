import streamlit as st
import fastf1
import pandas as pd

@st.cache_data(show_spinner="Récupération du calendrier F1...")
def get_calendar(year):
    calendar = fastf1.get_event_schedule(year)
    
    df_calendar = calendar.copy()

    colonnes = [
        'RoundNumber','Country','Location','EventDate','EventName',
        'Session1','Session1DateUtc','Session2','Session2DateUtc',
        'Session3','Session3DateUtc','Session4','Session4DateUtc',
        'Session5','Session5DateUtc'
    ]
    
    df_calendar = df_calendar[colonnes]

    sessions_cols = ['Session1DateUtc', 'Session2DateUtc', 'Session3DateUtc','Session4DateUtc', 'Session5DateUtc']
    
    df_calendar['EventDate'] = pd.to_datetime(df_calendar['EventDate'])
    
    for col in sessions_cols:
        df_calendar[col] = pd.to_datetime(df_calendar[col]) + pd.Timedelta(hours=1)

    return df_calendar