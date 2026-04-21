import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
from mplsoccer import VerticalPitch, FontManager, add_image
from matplotlib.colors import LinearSegmentedColormap
from urllib.request import urlopen
import requests
from highlight_text import ax_text
from PIL import Image

from functions import get_event_data, get_competitions, get_season_teams, fetch_player_stats
import streamlit as st
import os

st.set_page_config(page_title="Player Pressing Dashboard", page_icon=":soccer:")

# Set environment variables from secrets for use in function.py and Sbapi
if "statsbomb" in st.secrets:
    os.environ["SB_USERNAME"] = st.secrets["statsbomb"]["username"]
    os.environ["SB_PASSWORD"] = st.secrets["statsbomb"]["password"]


st.title("Shot Placement Analysis")

# Initialize session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# Robustness check removed to prevent state reset
# if st.session_state.data_loaded and 'pdf_raw' not in st.session_state:
#     st.session_state.data_loaded = False

# Fetch available competitions dynamically
competitions_df = get_competitions()

# Select Competition
competition_names = competitions_df['competition_name'].unique()
selected_league_name = st.selectbox("Select competition", competition_names, index=0)

# Filter for seasons based on selected competition
seasons_df = competitions_df[competitions_df['competition_name'] == selected_league_name]
season_names = seasons_df['season_name'].unique()
selected_season_name = st.selectbox("Select season", season_names, index=0)

# Get the IDs for the selected combination
selected_row = seasons_df[seasons_df['season_name'] == selected_season_name].iloc[0]
competition_id = int(selected_row['competition_id'])
season_id = int(selected_row['season_id'])

# Fetch available teams for the selected season
team_names = get_season_teams(season_id, competition_id)
selected_team_name = st.selectbox("Select Team", team_names, index=0)

# --- LOAD DATA BUTTON ---
if st.button("Load Team Data", key="load_data_button"):
    # Create progress bar and status text
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(progress, message):
        progress_bar.progress(progress)
        status_text.text(message)
        
    # Fetch Event Data for specific team
    st.session_state.df = get_event_data(season_id, competition_id, team_name=selected_team_name, progress_callback=update_progress)

    # Fetch Player Stats to get known names
    pdf = fetch_player_stats(season_id, competition_id, team_name=selected_team_name)
    if pdf is not None and not pdf.empty and not st.session_state.df.empty:
        # Merge player_known_name into the main dataframe
        st.session_state.df = st.session_state.df.merge(
            pdf[['player_name', 'player_known_name']], 
            on='player_name', 
            how='left'
        )

    # Store Context
    st.session_state.df_teamNameId = pd.read_csv("teams_name_and_id_Statsbomb_Names.csv")
    st.session_state.selected_league = selected_league_name
    st.session_state.selected_season = selected_season_name
    st.session_state.data_loaded = True
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    st.success("Data Loaded Successfully!")

if st.session_state.data_loaded:
    if not st.session_state.df.empty:
        # Player selector with known names
        # Create a mapping or just use the display name column if we merged it earlier
        if 'player_known_name' in st.session_state.df.columns:
             # Use known name if available, else fallback to player_name
             st.session_state.df['display_name'] = st.session_state.df['player_known_name'].fillna(st.session_state.df['player_name'])
        else:
             st.session_state.df['display_name'] = st.session_state.df['player_name']

        player_names = st.session_state.df['display_name'].dropna().unique()
        selected_player = st.selectbox("Select Player", player_names, index=0)
        
        if selected_player:
            # Import visuals
            from visuals import plot_shot_analysis
            
            # Generate and show plot
            # Pass the selected player (which is now display_name) to the visual function
            # We need to ensure the visual function uses 'display_name' or we map it back.
            # Easiest: Let visuals.py filter by 'display_name' if available. 
            # Or better: FILTER THE DF HERE and pass the subset to the function.
            # But the function does more processing. 
            # Let's just update the visual function signature later? Or assume it uses the column.
            # Actually, let's keep it simple: filter the DF here for just that player and pass it?
            # No, the function expects the full DF usually? No, it filters inside.
            # Let's update `visuals.py` to filter on `display_name` if possible.
            
            # For now, let's assume the column `display_name` exists in `st.session_state.df` because we just added it.
            # We will modify visuals.py to use `display_name` for filtering.
            fig = plot_shot_analysis(st.session_state.df, selected_player, selected_season_name, selected_team_name, selected_league_name)
            if fig:
                st.pyplot(fig)

            else:
                st.warning("No data found for selected player.")