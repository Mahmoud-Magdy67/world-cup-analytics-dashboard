"""
UPDATED: Player Analysis page - Shows top 500 players from all World Cup nations
"""
from pages._shared import *

page_header('Player Analysis', 'Identify standout players by goals, assists, chance creation, and minutes played.')

# Fetch top 500 players from BigQuery
df = get_players()

# KPI Cards
total_goals = int(df['goals'].sum()) if 'goals' in df.columns else 0
total_assists = int(df['assists'].sum()) if 'assists' in df.columns else 0
total_players = len(df)

kpi_cards([
    ("Players tracked", total_players, "Top 500 scorers from World Cup nations"),
    ("Total goals", total_goals, "Across all players"),
    ("Total assists", total_assists, "Across all players")
])

# Top Scorers Chart
st.subheader("Top Player Goal Contributions")
st.caption("Showing top 20 players by goals + assists")

# Prepare data for chart
chart_df = df.head(20).copy()
chart_df['total_contributions'] = chart_df['goals'] + chart_df['assists']

# Create grouped bar chart
fig = px.bar(
    chart_df.melt(id_vars=['player_name'], value_vars=['goals', 'assists']),
    x="player_name",
    y="value",
    color="variable",
    barmode="group",
    title="Goal Contributions by Player (Top 20)",
    labels={"player_name": "Player", "value": "Count", "variable": "Statistic"},
    color_discrete_map={"goals": "#1f77b4", "assists": "#aec7e8"}
)
fig.update_layout(height=500, xaxis_tickangle=-45)

st.plotly_chart(fig, use_container_width=True)

# Full Data Table
st.subheader("All Player Statistics")
st.caption(f"Showing all {total_players} players sorted by goals")

# Select and format columns
display_cols = ["player_name", "nation_code", "position", "club_team", "goals", "assists", "xg", "xa"]
if 'minutes' in df.columns:
    display_cols.append('minutes')
if 'matches_played' in df.columns:
    display_cols.append('matches_played')
if 'age' in df.columns:
    display_cols.append('age')

display_df = df[display_cols].copy()

# Format numeric columns
for col in ['goals', 'assists']:
    if col in display_df.columns:
        display_df[col] = display_df[col].fillna(0).astype(int)

for col in ['xg', 'xa']:
    if col in display_df.columns:
        display_df[col] = display_df[col].round(2)

if 'minutes' in display_df.columns:
    display_df['minutes'] = display_df['minutes'].fillna(0).astype(int)

if 'matches_played' in display_df.columns:
    display_df['matches_played'] = display_df['matches_played'].fillna(0).astype(int)

# Display table
st.dataframe(display_df, use_container_width=True, hide_index=True)

# Additional insights
st.subheader("Player Insights")
col1, col2, col3, col4 = st.columns(4)

with col1:
    top_scorer = df.iloc[0]['player_name'] if len(df) > 0 else "N/A"
    top_scorer_goals = df.iloc[0]['goals'] if len(df) > 0 else 0
    st.metric("Top Scorer", f"{top_scorer}", f"{int(top_scorer_goals)} goals")

with col2:
    top_assister = df.loc[df['assists'].idxmax()] if len(df) > 0 and 'assists' in df.columns else None
    if top_assister is not None:
        st.metric("Top Assister", f"{top_assister['player_name']}", f"{int(top_assister['assists'])} assists")
    else:
        st.metric("Top Assister", "N/A", "")

with col3:
    avg_age = df['age'].mean() if 'age' in df.columns and len(df) > 0 else 0
    st.metric("Average Age", f"{avg_age:.1f} years")

with col4:
    positions = df['position'].value_counts() if 'position' in df.columns else {}
    most_common_pos = positions.idxmax() if len(positions) > 0 else "N/A"
    st.metric("Most Common Position", most_common_pos)

# Top players by position
st.subheader("Top Players by Position")
if 'position' in df.columns:
    positions = df['position'].unique()
    tabs = st.tabs([f"{pos} ({len(df[df['position']==pos])})" for pos in positions[:5]])
    
    for i, pos in enumerate(positions[:5]):
        with tabs[i]:
            pos_df = df[df['position'] == pos].head(10)
            st.dataframe(pos_df[['player_name', 'nation_code', 'club_team', 'goals', 'assists', 'xg', 'xa']], use_container_width=True, hide_index=True)
