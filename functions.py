import pandas as pd
import requests
import os
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
from highlight_text import ax_text
from mplsoccer import VerticalPitch
from mplsoccer import Sbapi

import concurrent.futures
import streamlit as st

@st.cache_data
def get_competitions():
    username = os.getenv('SB_USERNAME')
    password = os.getenv('SB_PASSWORD')
    parser = Sbapi(dataframe=True, username=username, password=password)
    return parser.competition()


@st.cache_data
def get_season_teams(season_id, competition_id):
    username = os.getenv('SB_USERNAME')
    password = os.getenv('SB_PASSWORD')
    parser = Sbapi(dataframe=True, username=username, password=password)
    try:
        df_match = parser.match(competition_id=competition_id, season_id=season_id)
        if df_match.empty:
            return []
        teams = set(df_match['home_team_name'].dropna()).union(set(df_match['away_team_name'].dropna()))
        return sorted(list(teams))
    except:
        return []

def fetch_single_match(parser, mid, team_name=None):
    try:
        # parser.event returns a tuple of (events, related, freeze, tactics)
        # We only need the first element (events dataframe)
        event_data = parser.event(mid)
        if isinstance(event_data, tuple):
            df_event = event_data[0]
        else:
            df_event = event_data
            
        cols = ['id', 'type_name', 'outcome_name',
               'play_pattern_name', 'team_name', 'player_name', 'player_position_name',
               'x', 'y', 'z', 'end_x', 'end_y', 'end_z', 'body_part_name', 'sub_type_name', 'technique_name',
               'shot_statsbomb_xg', 'shot_first_time', 'shot_statsbomb_xg2', ]
        # Ensure columns exist before selecting
        existing_cols = [c for c in cols if c in df_event.columns]
        df_event = df_event[existing_cols]
        if team_name:
            # Filter for Shot type, specific team, excluding headers and blocked/wayward shots
            df_event = df_event[
                (df_event['type_name'] == 'Shot') & 
                (df_event['team_name'] == team_name) & 
                (df_event['body_part_name'] != 'Head') & 
                (df_event['sub_type_name'] == 'Open Play') &
                (~df_event['outcome_name'].isin(['Blocked', 'Wayward']))
            ]
        else:
            df_event = df_event[df_event['type_name'] == 'Shot']
        return df_event
    except Exception:
        return None

def get_event_data(season_id, competition_id, team_name=None, progress_callback=None):
    username = os.getenv('SB_USERNAME')
    password = os.getenv('SB_PASSWORD')
    parser = Sbapi(dataframe=True, username=username, password=password)
    
    try:
        df_match = parser.match(competition_id=competition_id, season_id=season_id)
        
        if df_match.empty:
            return pd.DataFrame()
            
        df_match = df_match[['match_id', 'home_team_name', 'away_team_name', 'match_status']]
        
        # Filter by Team if provided
        if team_name:
            df_match = df_match[(df_match['home_team_name'] == team_name) | (df_match['away_team_name'] == team_name)]
            
        status_filter = ['Completed', 'available', 'Available']
        df_match = df_match[df_match['match_status'].isin(status_filter)]
        mids = df_match['match_id'].unique()
        total_matches = len(mids)
        
        if progress_callback:
            progress_callback(0, f"Found {total_matches} matches for {team_name if team_name else 'season'}. Starting parallel download...")
            
    except Exception as e:
        return pd.DataFrame()

    all_event = []
    
    # Use ThreadPoolExecutor to fetch matches in parallel
    # API Limit: 15,000 requests / 5 mins (~50 req/sec). 
    # Increasing workers to 50 to maximize throughput.
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        # Map each match ID to a future
        future_to_mid = {executor.submit(fetch_single_match, parser, mid, team_name): mid for mid in mids}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_mid)):
            result = future.result()
            if result is not None:
                all_event.append(result)
            
            if progress_callback:
                progress_callback((i + 1) / total_matches, f"Processed {i+1}/{total_matches} matches")

    if all_event:
        df = pd.concat(all_event, ignore_index=True)
    else:
        df = pd.DataFrame()
    
    return df

@st.cache_data
def fetch_player_stats(season_id, competition_id, team_name=None, username=None, password=None):
    if username is None:
        username = os.getenv('SB_USERNAME')
    if password is None:
        password = os.getenv('SB_PASSWORD')

    url = f"https://data.statsbombservices.com/api/v4/competitions/{competition_id}/seasons/{season_id}/player-stats"
    
    if username and password:
        response = requests.get(url, auth=(username, password))
    else:
        print("Warning: No StatsBomb credentials provided. Attempting public access.")
        response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return None
    
    pdf = pd.DataFrame(response.json())

    pdf.columns = pdf.columns.str.replace('player_season_', '', regex=False)
    pdf = pdf[['player_name', 'player_known_name', 'team_name']]
    pdf['player_known_name'] = pdf['player_known_name'].fillna(pdf['player_name'])
    pdf = pdf[pdf['team_name'] == team_name]
    return pdf

