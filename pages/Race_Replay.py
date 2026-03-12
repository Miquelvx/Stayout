import streamlit as st
import fastf1
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os

# ----------------------------
# CONFIG FASTF1 CACHE
# ----------------------------

if not os.path.exists('f1_cache'):
    os.makedirs('f1_cache')

fastf1.Cache.enable_cache('f1_cache')

STEP_VISUAL = 0.3

st.set_page_config(page_title="F1 Race Replay", layout="wide")

# ----------------------------
# LOAD SESSION
# ----------------------------

@st.cache_resource
def load_full_session(year, gp):

    try:
        session = fastf1.get_session(year, gp, 'R')
        session.load(telemetry=True, weather=False, messages=False)
        return session
    except:
        return None


# ----------------------------
# LEADERBOARD
# ----------------------------

@st.cache_data
def build_leaderboard(_session, lap_num):
    """
    Leaderboard à la fin du tour lap_num
    Colonnes : Pos, Num, Code, Pneus, Gap
    """

    laps = _session.laps

    # pick_laps pour récupérer le tour
    lap_data = laps.pick_laps(lap_num)

    if lap_data.empty:
        return pd.DataFrame(columns=["Pos","Num","Code","Pneus","Gap"])

    # Leader
    leader_row = lap_data.sort_values("Position").iloc[0]
    leader_time = leader_row["Time"]

    lb = []

    # Boucle sur tous les pilotes présents dans ce tour
    for _, row in lap_data.iterrows():
        try:
            pos = int(row["Position"])
            drv_code = row["Driver"]
            compound = row.get("Compound", "Unknown")
            time = row["Time"]

            driver_info = _session.get_driver(drv_code)
            number = driver_info.get("DriverNumber", None)

            if pos == 1:
                gap = "LEADER"
            else:
                gap_sec = (time - leader_time).total_seconds()
                gap = f"+{gap_sec:.3f}s"

            lb.append({
                "Pos": pos,
                "Num": number,
                "Code": drv_code,
                "Pneus": compound,
                "Gap": gap
            })

        except Exception as e:
            continue

    df = pd.DataFrame(lb)

    return df.sort_values("Pos").reset_index(drop=True)


# ----------------------------
# TELEMETRY SYNC
# ----------------------------

@st.cache_data
def get_synced_data(_session, lap_num, n_drivers):

    laps = _session.laps
    drivers = _session.drivers[:n_drivers]

    # ----------------------------
    # REFERENCE TIME
    # ----------------------------

    if lap_num == 0:

        first_lap_all = laps.pick_lap(1)
        start_ref = first_lap_all['Time'].min() - first_lap_all['LapTime'].median()
        duration = 120

        leader_current_lap = laps.pick_lap(1).sort_values('Position').iloc[0]

    else:

        if lap_num == 1:

            first_lap_all = laps.pick_lap(1)
            start_ref = first_lap_all['Time'].min() - first_lap_all['LapTime'].median()

        else:

            leader_prev_lap = laps.pick_lap(lap_num - 1).sort_values('Position').iloc[0]
            start_ref = leader_prev_lap['Time']

        leader_current_lap = laps.pick_lap(lap_num).sort_values('Position').iloc[0]

        duration = leader_current_lap['LapTime'].total_seconds() + 10

    end_ref = start_ref + pd.Timedelta(seconds=duration)

    # ----------------------------
    # CIRCUIT TRACE
    # ----------------------------

    circuit_df = leader_current_lap.get_telemetry().add_relative_distance()[['X', 'Y']]

    # ----------------------------
    # TELEMETRY DRIVERS
    # ----------------------------

    combined = []

    for drv in drivers:

        try:

            tel = laps.pick_driver(drv).get_telemetry()

            mask = (tel['SessionTime'] >= start_ref) & (tel['SessionTime'] <= end_ref)
            slice_tel = tel.loc[mask].copy()

            if slice_tel.empty:
                continue

            slice_tel['SyncSec'] = (slice_tel['SessionTime'] - start_ref).dt.total_seconds()
            slice_tel = slice_tel.set_index('SyncSec')

            new_idx = np.arange(0, duration, STEP_VISUAL)

            slice_tel = (
                slice_tel
                .reindex(slice_tel.index.union(new_idx))
                .interpolate('linear')
                .loc[new_idx]
            )

            slice_tel['Driver'] = drv
            slice_tel['TimeFrame'] = slice_tel.index.round(2)

            combined.append(
                slice_tel.reset_index()[['TimeFrame', 'X', 'Y', 'Driver']]
            )

        except:
            continue

    tel_df = pd.concat(combined)

    return circuit_df, tel_df


# ----------------------------
# SIDEBAR
# ----------------------------

st.sidebar.title("⏱️ Live Sync Control")

year = st.sidebar.selectbox("Année", [2024, 2023, 2022], index=1)

gp = st.sidebar.text_input("Grand Prix", "Zandvoort")

session = load_full_session(year, gp)

if session is None:

    st.error("Session non trouvée.")

else:

    max_laps = int(session.laps['LapNumber'].max())

    selected_lap = st.sidebar.select_slider(
        "Tour de référence",
        options=range(1, int(session.laps['LapNumber'].max())+1),
        value=1
    )

    num_drivers = 20

    circuit_df, tel_df = get_synced_data(session, selected_lap, num_drivers)

    leaderboard = build_leaderboard(session, selected_lap)

    # ----------------------------
    # LAYOUT
    # ----------------------------

    col_map, col_lb = st.columns([3, 1])

    # ----------------------------
    # TRACK MAP
    # ----------------------------

    with col_map:

        if selected_lap == 0:
            st.subheader("🚥 Tour de formation")
        else:
            st.subheader(f"🏁 Tour {selected_lap}")

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=circuit_df['X'],
                y=circuit_df['Y'],
                mode='lines',
                line=dict(color='rgba(255,255,255,0.1)', width=2),
                hoverinfo='skip'
            )
        )

        times = sorted(tel_df['TimeFrame'].unique())

        for drv in tel_df['Driver'].unique():

            pos = tel_df[
                (tel_df['Driver'] == drv) &
                (tel_df['TimeFrame'] == times[0])
            ]

            fig.add_trace(
                go.Scatter(
                    x=pos['X'],
                    y=pos['Y'],
                    mode='markers+text',
                    text=drv,
                    textposition="top center",
                    name=drv,
                    marker=dict(size=12, line=dict(width=1, color='white'))
                )
            )

        frames = []

        for t in times[::2]:

            frame_data = [go.Scatter(x=circuit_df['X'], y=circuit_df['Y'])]

            for drv in tel_df['Driver'].unique():

                p = tel_df[
                    (tel_df['Driver'] == drv) &
                    (tel_df['TimeFrame'] == t)
                ]

                frame_data.append(go.Scatter(x=p['X'], y=p['Y']))

            frames.append(go.Frame(data=frame_data, name=str(t)))

        fig.frames = frames

        fig.update_layout(
            template="plotly_dark",
            height=800,
            yaxis=dict(scaleanchor="x", scaleratio=1),
            updatemenus=[{
                "type": "buttons",
                "buttons": [{
                    "label": "▶ Lancer la Synchro",
                    "method": "animate",
                    "args": [None, {
                        "frame": {"duration": 150, "redraw": False},
                        "fromcurrent": True,
                        "transition": {"duration": 140, "easing": "linear"}
                    }]
                }]
            }]
        )

        st.plotly_chart(fig, use_container_width=True)

    # ----------------------------
    # LEADERBOARD
    # ----------------------------

    with col_lb:

        st.subheader("📊 Leaderboard")

        st.dataframe(leaderboard, hide_index=True, use_container_width=True)

        if selected_lap == 0:
            st.info("Grille de départ – tour de formation")
        else:
            st.info("Classement à la fin du tour")
    