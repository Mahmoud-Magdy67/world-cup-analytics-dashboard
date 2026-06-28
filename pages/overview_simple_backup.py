"""
UPDATED: Tournament Overview page - Shows ALL 48 teams
"""
from pages._shared import *

page_header('Tournament Overview', 'High-level tournament health, scoring trends, and leading contenders.')

# Fetch all teams from BigQuery
df = get_teams()

# KPI Cards
kpi_cards([
    ("Teams tracked", len(df), "All 48 World Cup teams"),
    ("Top contender", df.iloc[0].team_name, f"{df.iloc[0].championship_probability:.1%}"),
    ("Highest rated", df.loc[df.elo_rating.idxmax()].team_name, f"{int(df.elo_rating.max())} elo")
])

# Championship Probability Chart - Show TOP 12 for clarity
st.subheader("Championship Probability by Team")
st.plotly_chart(
    px.bar(
        df.head(12),  # Top 12 for chart readability
        x="team_name",
        y="championship_probability",
        color="contender_tier",
        title="Top 12 Teams - Championship Probability",
        labels={"team_name": "Team", "championship_probability": "Probability"}
    ),
    width='stretch'
)

# Full Data Table - Show ALL 48 teams
st.subheader("All Teams Rankings")
st.caption(f"Showing all {len(df)} teams")

display_df = df[[
    "team_name",
    "group_name", 
    "winner_rank",
    "championship_probability",
    "elo_rating",
    "contender_tier"
]].copy()

# Format probability as percentage
display_df['championship_probability_pct'] = (display_df['championship_probability'] * 100).round(2).astype(str) + '%'
display_df['elo_rating'] = display_df['elo_rating'].round(0).astype(int)

# Display with better formatting
st.dataframe(
    display_df.rename(columns={
        'championship_probability_pct': 'Win Probability',
        'elo_rating': 'ELO',
        'team_name': 'Team',
        'group_name': 'Group',
        'winner_rank': 'Rank',
        'contender_tier': 'Tier'
    }),
    width='stretch',
    hide_index=True
)

# Additional insights
st.subheader("Tournament Insights")
col1, col2, col3 = st.columns(3)

with col1:
    top5 = df.head(5)['team_name'].tolist()
    st.metric("Top 5 Favorites", ", ".join(top5))

with col2:
    dark_horses = df[(df['championship_probability'] >= 0.01) & (df['championship_probability'] < 0.03)]
    st.metric("Dark Horses (>1%)", len(dark_horses))

with col3:
    confederations = df.groupby('group_name').size()
    st.metric("Groups", len(confederations))
