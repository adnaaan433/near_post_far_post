import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
from highlight_text import ax_text
import pandas as pd
import numpy as np

def plot_shot_analysis(df, player_name, season_name, team_name, league_name):
    # Determine the column to filter on
    if 'display_name' in df.columns:
        filter_col = 'display_name'
    elif 'player_known_name' in df.columns:
        # If display_name not created but known_name exists (e.g. reused df), fallback
        df['display_name'] = df['player_known_name'].fillna(df['player_name'])
        filter_col = 'display_name'
    else:
        filter_col = 'player_name'
        
    # Filter for the specific player using the determined column
    df_player = df[df[filter_col] == player_name].copy()
    
    if df_player.empty:
        return None
    
    # Define Dimensions
    # Pitch is 80 wide, 120 long.
    # Goal center is 40.
    # Left (from attacking view) is y < 40. Right is y > 40.
    
    # Calculate Shot Side and Target Side
    # Shot Side: Where the player is.
    df_player['shot_side'] = np.where(df_player['y'] <= 40, 'Left', 'Right')
    
    # Target Side: Where the projected ball would cross the goal line (x=120)
    # Estimated End Location based on slope
    df_player['estimated_end_x'] = 120
    
    # Calculate slope: m = (y2 - y1) / (x2 - x1)
    # estimated_y = y1 + m * (120 - x1)
    
    # Prevent division by zero if x is same (unlikely for goal shots, but good practice)
    delta_x = df_player['end_x'] - df_player['x']
    # Avoid zero division by replacing 0 with NaN temporarily
    slope = (df_player['end_y'] - df_player['y']) / delta_x.replace(0, np.nan)
    
    df_player['estimated_end_y'] = df_player['y'] + slope * (120 - df_player['x'])
    
    # Fallback for vertical shots or errors: usage actual end_y
    df_player['estimated_end_y'].fillna(df_player['end_y'], inplace=True)

    # Zone Definitions (Moved up for logic usage)
    zones = {
        'Left': {'color': '#ffb3b3', 'edgecolor': '#ff0000', 'label': 'Left Zone', 'x_range': (80, 120), 'y_range': (18, 36)}, # Red-ish
        'Right': {'color': '#b3d9ff', 'edgecolor': '#0066cc', 'label': 'Right Zone', 'x_range': (80, 120), 'y_range': (44, 62)}  # Blue-ish
    }

    # Filter conditions for START location
    # Left Zone Start: y in [18, 36], x in [80, 120]
    in_left_zone = (df_player['y'] >= zones['Left']['y_range'][0]) & (df_player['y'] <= zones['Left']['y_range'][1]) & \
                   (df_player['x'] >= zones['Left']['x_range'][0]) & (df_player['x'] <= zones['Left']['x_range'][1])
    
    # Right Zone Start: y in [44, 62], x in [80, 120]
    in_right_zone = (df_player['y'] >= zones['Right']['y_range'][0]) & (df_player['y'] <= zones['Right']['y_range'][1]) & \
                    (df_player['x'] >= zones['Right']['x_range'][0]) & (df_player['x'] <= zones['Right']['x_range'][1])
    
    # Target Conditions
    val_8_3 = 8/3
    
    # Near Post Logic
    # NP1 (Left): 18 < end_y < 36 + 8/3
    np_target_left = (df_player['estimated_end_y'] > 18) & (df_player['estimated_end_y'] < (36 + val_8_3))
    # NP2 (Right): 44 - 8/3 < end_y < 62
    np_target_right = (df_player['estimated_end_y'] > (44 - val_8_3)) & (df_player['estimated_end_y'] < 62)
    
    # Far Post Logic
    # FP1 (Left): 44 - 8/3 < end_y < 62
    fp_target_left = (df_player['estimated_end_y'] > (44 - val_8_3)) & (df_player['estimated_end_y'] < 62)
    # FP2 (Right): 18 < end_y < 36 + 8/3
    fp_target_right = (df_player['estimated_end_y'] > 18) & (df_player['estimated_end_y'] < (36 + val_8_3))
    
    # Assign Origin Zone for color coding later
    df_player['origin_zone'] = np.nan
    df_player.loc[in_left_zone, 'origin_zone'] = 'Left'
    df_player.loc[in_right_zone, 'origin_zone'] = 'Right'
    
    # Combine conditions
    near_post_shots = df_player[
        (in_left_zone & np_target_left) | 
        (in_right_zone & np_target_right)
    ].copy()
    
    far_post_shots = df_player[
        (in_left_zone & fp_target_left) | 
        (in_right_zone & fp_target_right)
    ].copy()
    
    total_shots = len(df_player)
    pct_near = (len(near_post_shots) / total_shots * 100) if total_shots > 0 else 0
    pct_far = (len(far_post_shots) / total_shots * 100) if total_shots > 0 else 0
    
    # Create Figure with 2 rows: Top for Pitch, Bottom for Goal
    pitch = VerticalPitch(half=True, goal_type='box', pitch_color='white', line_color='black')
    
    # Manually create figure and axes
    # Manually create figure and axes
    fig = plt.figure(figsize=(16, 12))
    # Goal (Top) height ratio small, Pitch (Bottom) height ratio large.
    gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 5], hspace=-0.4)
    
    ax_goal_left = fig.add_subplot(gs[0, 0])
    ax_goal_right = fig.add_subplot(gs[0, 1])
    ax_pitch_left = fig.add_subplot(gs[1, 0])
    ax_pitch_right = fig.add_subplot(gs[1, 1])
    
    # Draw pitches on top row
    pitch.draw(ax=ax_pitch_left)
    pitch.draw(ax=ax_pitch_right)
    
    datasets = [
        {'title': f'Near Post ({pct_near:.0f}% Shots)', 'data': near_post_shots, 'pitch_ax': ax_pitch_left, 'goal_ax': ax_goal_left},
        {'title': f'Far Post ({pct_far:.0f}% Shots)', 'data': far_post_shots, 'pitch_ax': ax_pitch_right, 'goal_ax': ax_goal_right}
    ]
    
    for item in datasets:
        pitch_ax = item['pitch_ax']
        goal_ax = item['goal_ax']
        data = item['data']
        goal_ax.set_title(item['title'], fontsize=15, fontweight='bold', pad=20)
        
        subset_data = []
        
        # --- PITCH PLOT ---
        # Draw Zones
        for side, z in zones.items():
            rect_x = z['y_range'][0]
            rect_y = z['x_range'][0]
            rect_width = z['y_range'][1] - z['y_range'][0]
            rect_height = z['x_range'][1] - z['x_range'][0]
            
            rect = plt.Rectangle((rect_x, rect_y), rect_width, rect_height,
                                 facecolor=z['color'], edgecolor=z['edgecolor'], alpha=0.3, zorder=1, linestyle='--')
            pitch_ax.add_patch(rect)
            
            # Filter data for this zone based on coordinates AND matching side in logic
            # Note: 'data' is already filtered for Near or Far post logic.
            # We just want to find which shots CAME from this zone to plot lines/scatters correctly?
            # Actually, we can just mask using origin_zone.
            
            zone_data = data[data['origin_zone'] == side]
            subset_data.append(zone_data)
            
            # Calculate Stats
            n_shots = len(zone_data)
            xg_sum = zone_data['shot_statsbomb_xg'].sum()
            
            # Draw Shots Lines on Pitch
            if not zone_data.empty:
                pitch.lines(zone_data.estimated_end_x, zone_data.estimated_end_y, zone_data.x, zone_data.y, 
                            ax=pitch_ax, color='gray', alpha=0.6, lw=2, comet=True)
                
                # Plot Goals/Misses on Pitch
                goals = zone_data[zone_data['outcome_name'] == 'Goal']
                misses = zone_data[zone_data['outcome_name'] != 'Goal']
                
                pitch.scatter(goals.x, goals.y, ax=pitch_ax, s=(goals['shot_statsbomb_xg'] * 500) + 100, 
                              c='#228B22', zorder=2, edgecolors='black')
                pitch.scatter(misses.x, misses.y, ax=pitch_ax, s=(misses['shot_statsbomb_xg'] * 500) + 50, 
                              c='white', edgecolors='black', zorder=2, alpha=0.8)

            # Add Text Stats
            text_x = (z['y_range'][0] + z['y_range'][1]) / 2
            text_y = z['x_range'][0] - 2.5
            stat_color = '#d9534f' if side == 'Left' else '#0275d8'
            stats_str = f"<{z['label']}>\n<{n_shots} Shots ({xg_sum:.2f} xG)>"
            ax_text(text_x, text_y, stats_str, color=stat_color, 
                    ha='center', va='top', ax=pitch_ax, fontsize=10, highlight_textprops=[{'weight': 'bold'}, {}])
            
        if subset_data:
            combined_zone_data = pd.concat(subset_data)
            total_xg_sum = combined_zone_data['shot_statsbomb_xg'].sum()
            # Calculate xGOT from 'shot_statsbomb_xg2' if it exists, otherwise 0
            if 'shot_statsbomb_xg2' in combined_zone_data.columns:
                total_xgot = combined_zone_data['shot_statsbomb_xg2'].sum()
            else:
                total_xgot = 0.0
                
            total_goals_data = combined_zone_data[combined_zone_data['outcome_name'] == 'Goal']
            total_n_goals = len(total_goals_data)
        else:
            total_n_goals = 0
            total_xg_sum = 0
            total_xgot = 0
            combined_zone_data = pd.DataFrame()
            
        pitch_ax.text(40, 60, f"{total_n_goals} Goals\n{total_xg_sum:.2f} xG\n{total_xgot:.2f} xGOT", 
                ha='center', va='center', fontsize=14, color='green', fontweight='bold',
                bbox=dict(facecolor='white', edgecolor='gray', boxstyle='circle,pad=0.5', alpha=0.9))

        # --- GOAL MOUTH PLOT ---
        # Setup Axes
        goal_ax.set_ylim(-0.5, 3.5) # Height
        goal_ax.set_xlim(46, 34) # Inverted perspective? No, relying on standard cartesian for now.
        goal_ax.set_xlim(34, 46) # 36 is Left. Left-to-Right.
        goal_ax.set_aspect('equal')
        goal_ax.axis('off')
        
        # Draw Goal Net (Grid Structure)
        # Vertical lines
        x_net_coords = np.linspace(36, 44, 25)
        for xn in x_net_coords:
            goal_ax.plot([xn, xn], [0, 2.67], color='#A9A9A9', lw=0.5, alpha=0.4, zorder=0.5)
            
        # Horizontal lines
        y_net_coords = np.linspace(0, 2.67, 10)
        for yn in y_net_coords:
            goal_ax.plot([36, 44], [yn, yn], color='#A9A9A9', lw=0.5, alpha=0.4, zorder=0.5)

        # Draw Goal Posts
        # Posts at 36 and 44. Height 2.67.
        goal_posts = plt.Rectangle((36, 0), 8, 2.67, fill=False, edgecolor='black', lw=3, zorder=3)
        goal_ax.add_patch(goal_posts)
        
        # Draw Shading for Zones on Goal
        # Logic derived from logic.txt boundaries
        # Left Side Cutoff: 36 + 8/3 = 38.66
        # Right Side Cutoff: 44 - 8/3 = 41.33
        y_lim_goal = 2.67
        
        if "Near Post" in item['title']:
            # Near Post Logic: 
            # Left Zone (Red) -> Targets Left Side (< 38.66)
            # Right Zone (Blue) -> Targets Right Side (> 41.33)
            
            # Red Rect on Left Side [36, 38.66]
            rect_red = plt.Rectangle((36, 0), 2.66, y_lim_goal, facecolor=zones['Left']['color'], alpha=0.3, zorder=1)
            goal_ax.add_patch(rect_red)
            
            # Blue Rect on Right Side [41.33, 44]
            rect_blue = plt.Rectangle((41.33, 0), 2.66, y_lim_goal, facecolor=zones['Right']['color'], alpha=0.3, zorder=1)
            goal_ax.add_patch(rect_blue)
            
        elif "Far Post" in item['title']:
            # Far Post Logic:
            # Left Zone (Red) -> Targets Right Side (> 41.33)
            # Right Zone (Blue) -> Targets Left Side (< 38.66)
            
            # Red Rect on Right Side [41.33, 44]
            rect_red_far = plt.Rectangle((41.33, 0), 2.66, y_lim_goal, facecolor=zones['Left']['color'], alpha=0.3, zorder=1)
            goal_ax.add_patch(rect_red_far)
            
            # Blue Rect on Left Side [36, 38.66]
            rect_blue_far = plt.Rectangle((36, 0), 2.66, y_lim_goal, facecolor=zones['Right']['color'], alpha=0.3, zorder=1)
            goal_ax.add_patch(rect_blue_far)

        # Draw Ground Line
        goal_ax.plot([24, 56], [0, 0], color='black', lw=2, zorder=3)
        
        # Plot Shots on Goal Mouth
        if not combined_zone_data.empty:
            # Check for end_z existence, defaulting to 0 if missing
            z_vals = combined_zone_data['end_z'] if 'end_z' in combined_zone_data.columns else np.zeros(len(combined_zone_data))
            
            # Map colors: Goal=Green, else Zone Color (Light/Low Opacity Shade)
            conditions = [
                combined_zone_data['outcome_name'] == 'Goal',
                combined_zone_data['origin_zone'] == 'Left',
                combined_zone_data['origin_zone'] == 'Right'
            ]
            choices = ['#228B22', zones['Left']['color'], zones['Right']['color']]
            
            colors = np.select(conditions, choices, default='white')
            
            # Scatter Plot
            # x = estimated_end_y
            # y = end_z
            goal_ax.scatter(combined_zone_data['estimated_end_y'], z_vals, 
                            s=(combined_zone_data['shot_statsbomb_xg'] * 500) + 100,
                            c=colors, edgecolors='black', alpha=0.8, zorder=2)

    # Determine display name
    display_name = player_name
    if 'player_known_name' in df_player.columns:
        possible_name = df_player['player_known_name'].iloc[0]
        if pd.notna(possible_name):
            display_name = possible_name

    # Main Title
    # Main Title - Left Aligned
    fig.text(0.13, 1.05, f"{display_name}", fontsize=30, fontweight='bold', ha='left', va='top')
    fig.text(0.13, 1, f"for {team_name}, in {league_name} {season_name} season | Data: Statsbomb | made by: @adnaaan433\nOpen-Play Shots only (excluding Headers and Blocked Shots) | visit: shot-placement-analysis.streamlit.app", 
             fontsize=15, ha='left', va='top')
    fig.text(0.5, 0.25, "Circle Size represents xG of each shot | Green Circles represents Goals", fontsize=12, ha='center', va='top')
                 
    return fig
